"""Atomic GitHub publication contracts for Aura's Agent Bridge.

This module replaces workflow-based "materializers" with a bounded Git Data API
transport:

exact base/head -> blobs -> one tree -> one commit -> fast-forward ref -> PR.

Publication and merge authority remain separate. The publisher may create or
advance a feature branch and open/update a pull request only when explicitly
authorized. It never merges. Merge preparation emits a guarded connector packet
that requires a separate human-authorized action using the exact PR head SHA.
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

from aura_agent_arena_persistence_bridge import PersistentAuraAgentArenaBridge
from aura_agent_arena_errors import make_error_packet


GITHUB_PUBLICATION_VERSION = "AURA_AGENT_BRIDGE_GITHUB_PUBLICATION_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

_MAX_FILES = 512
_MAX_FILE_BYTES = 4 * 1024 * 1024
_MAX_TOTAL_BYTES = 32 * 1024 * 1024
_ALLOWED_MODES = frozenset({"100644", "100755"})
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_BRANCH_RE = re.compile(r"^(?!/)(?!.*//)(?!.*\.\.)(?!.*[~^:?*\[\\])[^\x00-\x20\x7f]+(?<!/)$")
_FORBIDDEN_TEMP_PREFIXES = (
    ".aura/tmp/",
    "scripts/.tmp/",
)
_FORBIDDEN_TEMP_SUFFIXES = (
    "_TEMP.md",
    "-temp.yml",
    "-temp.yaml",
    "_temp.yml",
    "_temp.yaml",
)


class GitHubPublicationError(ValueError):
    """Raised when a publication request violates a fail-closed contract."""


@dataclass(frozen=True)
class PublicationChange:
    """One canonical repository-tree mutation."""

    path: str
    operation: str
    mode: str
    content: str | None
    encoding: str
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
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _require_sha(value: Any, field: str) -> str:
    text = str(value or "").strip().lower()
    if not _SHA_RE.fullmatch(text):
        raise GitHubPublicationError(f"{field} must be a full lowercase 40-character Git SHA")
    return text


def _normalize_repo(value: Any) -> str:
    text = str(value or "").strip()
    if not _REPO_RE.fullmatch(text):
        raise GitHubPublicationError("repository_full_name must be owner/name")
    return text


def _normalize_branch(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text or len(text.encode("utf-8")) > 240 or not _BRANCH_RE.fullmatch(text):
        raise GitHubPublicationError(f"{field} is not a safe Git branch name")
    if text.endswith(".lock") or text.startswith("-"):
        raise GitHubPublicationError(f"{field} is not a safe Git branch name")
    return text


def _normalize_path(value: Any) -> str:
    raw = str(value or "").replace("\\", "/").strip()
    while raw.startswith("./"):
        raw = raw[2:]
    parts = raw.split("/")
    if (
        not raw
        or raw.startswith("/")
        or raw.endswith("/")
        or any(part in {"", ".", ".."} for part in parts)
        or parts[0] == ".git"
        or "\x00" in raw
    ):
        raise GitHubPublicationError(f"unsafe repository path: {value!r}")
    if len(raw.encode("utf-8")) > 1024:
        raise GitHubPublicationError("repository path exceeds 1024 UTF-8 bytes")
    return raw


def _is_temporary_transport(path: str) -> bool:
    lower = path.lower()
    return (
        any(lower.startswith(prefix.lower()) for prefix in _FORBIDDEN_TEMP_PREFIXES)
        or any(lower.endswith(suffix.lower()) for suffix in _FORBIDDEN_TEMP_SUFFIXES)
        or (
            lower.startswith(".github/workflows/")
            and any(marker in lower for marker in ("materialize", "bootstrap", "publisher", "trigger"))
        )
    )


def _content_bytes(content: Any, encoding: str) -> tuple[str, bytes]:
    if encoding == "utf-8":
        if not isinstance(content, str):
            raise GitHubPublicationError("utf-8 publication content must be a string")
        return content, content.encode("utf-8")
    if encoding == "base64":
        if not isinstance(content, str):
            raise GitHubPublicationError("base64 publication content must be a string")
        try:
            return content, base64.b64decode(content.encode("ascii"), validate=True)
        except (UnicodeEncodeError, ValueError) as exc:
            raise GitHubPublicationError("invalid base64 publication content") from exc
    raise GitHubPublicationError("encoding must be utf-8 or base64")


def _normalize_changes(
    raw_changes: Any,
    *,
    allow_temporary_transport: bool,
) -> list[PublicationChange]:
    if not isinstance(raw_changes, Sequence) or isinstance(raw_changes, (str, bytes, bytearray)):
        raise GitHubPublicationError("changes must be an array")
    if not 1 <= len(raw_changes) <= _MAX_FILES:
        raise GitHubPublicationError(f"changes must contain between 1 and {_MAX_FILES} entries")

    changes: list[PublicationChange] = []
    seen: set[str] = set()
    total_bytes = 0
    for index, item in enumerate(raw_changes):
        if not isinstance(item, Mapping):
            raise GitHubPublicationError(f"changes[{index}] must be an object")
        path = _normalize_path(item.get("path"))
        if path in seen:
            raise GitHubPublicationError(f"duplicate publication path: {path}")
        seen.add(path)

        if _is_temporary_transport(path) and not allow_temporary_transport:
            raise GitHubPublicationError(
                f"temporary workflow/transport artifact rejected: {path}"
            )

        operation = str(item.get("operation", "upsert")).strip().lower()
        if operation not in {"upsert", "delete"}:
            raise GitHubPublicationError("operation must be upsert or delete")
        mode = str(item.get("mode", "100644")).strip()
        if mode not in _ALLOWED_MODES:
            raise GitHubPublicationError(f"unsupported Git mode for {path}: {mode}")

        if operation == "delete":
            if item.get("content") not in (None, ""):
                raise GitHubPublicationError(f"delete entry must not include content: {path}")
            change = PublicationChange(
                path=path,
                operation=operation,
                mode=mode,
                content=None,
                encoding="utf-8",
                content_sha256=hashlib.sha256(b"").hexdigest(),
                byte_count=0,
            )
        else:
            encoding = str(item.get("encoding", "utf-8")).strip().lower()
            content, decoded = _content_bytes(item.get("content"), encoding)
            if len(decoded) > _MAX_FILE_BYTES:
                raise GitHubPublicationError(
                    f"{path} exceeds {_MAX_FILE_BYTES} decoded bytes"
                )
            total_bytes += len(decoded)
            if total_bytes > _MAX_TOTAL_BYTES:
                raise GitHubPublicationError(
                    f"publication exceeds {_MAX_TOTAL_BYTES} decoded bytes"
                )
            change = PublicationChange(
                path=path,
                operation=operation,
                mode=mode,
                content=content,
                encoding=encoding,
                content_sha256=hashlib.sha256(decoded).hexdigest(),
                byte_count=len(decoded),
            )
        changes.append(change)

    return sorted(changes, key=lambda change: change.path)


def compile_publication_contract(request_payload: Mapping[str, Any]) -> dict[str, Any]:
    """Compile a deterministic, connector-executable publication contract."""

    if not isinstance(request_payload, Mapping):
        raise GitHubPublicationError("publication request must be an object")

    repository = _normalize_repo(request_payload.get("repository_full_name"))
    mode = str(request_payload.get("publication_mode", "create")).strip().lower()
    if mode not in {"create", "update"}:
        raise GitHubPublicationError("publication_mode must be create or update")

    base_branch = _normalize_branch(request_payload.get("base_branch", "main"), "base_branch")
    head_branch = _normalize_branch(request_payload.get("head_branch"), "head_branch")
    if head_branch == base_branch:
        raise GitHubPublicationError("head_branch must differ from base_branch")

    expected_base_sha = _require_sha(
        request_payload.get("expected_base_sha"), "expected_base_sha"
    )
    expected_parent_sha = _require_sha(
        request_payload.get("expected_parent_sha", expected_base_sha),
        "expected_parent_sha",
    )
    if mode == "create" and expected_parent_sha != expected_base_sha:
        raise GitHubPublicationError(
            "create mode requires expected_parent_sha to equal expected_base_sha"
        )

    commit_message = str(request_payload.get("commit_message") or "").strip()
    pr_title = str(request_payload.get("pr_title") or "").strip()
    pr_body = str(request_payload.get("pr_body") or "")
    if not commit_message or len(commit_message.encode("utf-8")) > 4096:
        raise GitHubPublicationError("commit_message is required and must be <= 4096 bytes")
    if not pr_title or len(pr_title.encode("utf-8")) > 512:
        raise GitHubPublicationError("pr_title is required and must be <= 512 bytes")
    if len(pr_body.encode("utf-8")) > 256 * 1024:
        raise GitHubPublicationError("pr_body exceeds 256 KiB")

    allow_temporary_transport = bool(
        request_payload.get("allow_temporary_transport", False)
    )
    changes = _normalize_changes(
        request_payload.get("changes"),
        allow_temporary_transport=allow_temporary_transport,
    )

    publish_authorized = request_payload.get("publish_authorized") is True
    draft = request_payload.get("draft", True)
    if not isinstance(draft, bool):
        raise GitHubPublicationError("draft must be a boolean")

    public_request = {
        "version": GITHUB_PUBLICATION_VERSION,
        "repository_full_name": repository,
        "publication_mode": mode,
        "base_branch": base_branch,
        "head_branch": head_branch,
        "expected_base_sha": expected_base_sha,
        "expected_parent_sha": expected_parent_sha,
        "commit_message": commit_message,
        "pr_title": pr_title,
        "pr_body_sha256": hashlib.sha256(pr_body.encode("utf-8")).hexdigest(),
        "draft": draft,
        "changes": [change.public_dict() for change in changes],
        "allow_temporary_transport": allow_temporary_transport,
        "publish_authorized": publish_authorized,
    }
    contract_id = f"GHPUB-{_sha256(public_request)[:24]}"

    return {
        **public_request,
        "contract_id": contract_id,
        "change_count": len(changes),
        "total_bytes": sum(change.byte_count for change in changes),
        "branch_policy": "fresh_exact_base" if mode == "create" else "exact_parent_fast_forward",
        "transport": "github_git_data_api",
        "atomic_commit": True,
        "force_ref_update": False,
        "temporary_workflow_transport": False,
        "automatic_merge": False,
        "merge_authority": False,
        "human_review_required": True,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        "execution_status": "AUTHORIZED" if publish_authorized else "PROPOSAL_ONLY",
        "connector_sequence": [
            "resolve exact base/head ref",
            "resolve parent commit tree",
            "create bounded blobs",
            "create one tree from the exact parent tree",
            "create one commit with the exact expected parent",
            "create or fast-forward the feature ref without force",
            "create or update one pull request",
        ],
        "_private": {
            "pr_body": pr_body,
            "changes": changes,
        },
    }


class GitHubRestTransport:
    """Small GitHub REST transport with no token persistence or shell execution."""

    def __init__(
        self,
        *,
        token: str,
        api_root: str = "https://api.github.com",
        timeout_seconds: int = 30,
    ) -> None:
        token_text = str(token or "").strip()
        if not token_text:
            raise GitHubPublicationError("GitHub token is required for publication")
        normalized_root = str(api_root or "").rstrip("/")
        if normalized_root != "https://api.github.com":
            raise GitHubPublicationError(
                "public GitHub publication is pinned to https://api.github.com"
            )
        self._token = token_text
        self.api_root = normalized_root
        self.timeout_seconds = max(1, min(int(timeout_seconds), 120))

    def request(
        self,
        method: str,
        path: str,
        payload: Mapping[str, Any] | None = None,
        *,
        allow_404: bool = False,
    ) -> dict[str, Any] | None:
        url = f"{self.api_root}{path}"
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
        req = request.Request(url, method=method, data=data, headers=headers)
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                raw = response.read(8 * 1024 * 1024 + 1)
                if len(raw) > 8 * 1024 * 1024:
                    raise GitHubPublicationError("GitHub response exceeded 8 MiB")
                if not raw:
                    return {}
                parsed = json.loads(raw.decode("utf-8"))
                if not isinstance(parsed, dict):
                    raise GitHubPublicationError("GitHub response must be an object")
                return parsed
        except error.HTTPError as exc:
            if allow_404 and exc.code == 404:
                return None
            detail = exc.read(16 * 1024).decode("utf-8", errors="replace")
            raise GitHubPublicationError(
                f"GitHub API {method} {path} failed with HTTP {exc.code}: {detail[:2000]}"
            ) from exc
        except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise GitHubPublicationError(
                f"GitHub API {method} {path} failed: {exc}"
            ) from exc


def _repo_path(repository: str) -> str:
    owner, name = repository.split("/", 1)
    return f"/repos/{parse.quote(owner, safe='')}/{parse.quote(name, safe='')}"


def _git_ref_path(repository: str, branch: str) -> str:
    encoded = "/".join(parse.quote(part, safe="") for part in branch.split("/"))
    return f"{_repo_path(repository)}/git/ref/heads/{encoded}"


def _extract_ref_sha(payload: Mapping[str, Any], field: str) -> str:
    obj = payload.get("object")
    if not isinstance(obj, Mapping):
        raise GitHubPublicationError(f"{field} response omitted object")
    return _require_sha(obj.get("sha"), field)


def execute_publication_contract(
    contract: Mapping[str, Any],
    *,
    transport: GitHubRestTransport,
) -> dict[str, Any]:
    """Execute one authorized atomic publication contract. Never merges."""

    if not isinstance(contract, Mapping):
        raise GitHubPublicationError("contract must be an object")
    if contract.get("version") != GITHUB_PUBLICATION_VERSION:
        raise GitHubPublicationError("unsupported publication contract version")
    if contract.get("publish_authorized") is not True:
        raise GitHubPublicationError("publication is proposal-only; explicit authorization is required")
    if contract.get("automatic_merge") is not False:
        raise GitHubPublicationError("publication contract cannot contain merge authority")

    repository = _normalize_repo(contract.get("repository_full_name"))
    mode = str(contract.get("publication_mode"))
    base_branch = _normalize_branch(contract.get("base_branch"), "base_branch")
    head_branch = _normalize_branch(contract.get("head_branch"), "head_branch")
    expected_base_sha = _require_sha(contract.get("expected_base_sha"), "expected_base_sha")
    expected_parent_sha = _require_sha(
        contract.get("expected_parent_sha"), "expected_parent_sha"
    )
    private = contract.get("_private")
    if not isinstance(private, Mapping):
        raise GitHubPublicationError("contract private payload is unavailable")
    changes = private.get("changes")
    if not isinstance(changes, Sequence):
        raise GitHubPublicationError("contract changes are unavailable")

    base_ref = transport.request("GET", _git_ref_path(repository, base_branch))
    if not isinstance(base_ref, Mapping):
        raise GitHubPublicationError("base branch does not exist")
    observed_base_sha = _extract_ref_sha(base_ref, "base_ref")
    if observed_base_sha != expected_base_sha:
        raise GitHubPublicationError(
            f"base branch moved: expected {expected_base_sha}, observed {observed_base_sha}"
        )

    head_ref = transport.request(
        "GET", _git_ref_path(repository, head_branch), allow_404=True
    )
    if mode == "create":
        if head_ref is not None:
            raise GitHubPublicationError("create mode requires a fresh, nonexistent head branch")
        parent_sha = expected_base_sha
    else:
        if not isinstance(head_ref, Mapping):
            raise GitHubPublicationError("update mode requires an existing head branch")
        observed_head_sha = _extract_ref_sha(head_ref, "head_ref")
        if observed_head_sha != expected_parent_sha:
            raise GitHubPublicationError(
                f"head branch moved: expected {expected_parent_sha}, observed {observed_head_sha}"
            )
        parent_sha = observed_head_sha

    commit_data = transport.request(
        "GET", f"{_repo_path(repository)}/git/commits/{parent_sha}"
    )
    if not isinstance(commit_data, Mapping):
        raise GitHubPublicationError("parent commit was not returned")
    tree_data = commit_data.get("tree")
    if not isinstance(tree_data, Mapping):
        raise GitHubPublicationError("parent commit omitted tree")
    base_tree_sha = _require_sha(tree_data.get("sha"), "base_tree_sha")

    tree_elements: list[dict[str, Any]] = []
    for change in changes:
        if not isinstance(change, PublicationChange):
            raise GitHubPublicationError("contract contains an invalid change object")
        if change.operation == "delete":
            tree_elements.append(
                {"path": change.path, "mode": change.mode, "type": "blob", "sha": None}
            )
            continue
        blob_payload = {
            "content": change.content,
            "encoding": change.encoding,
        }
        blob = transport.request(
            "POST", f"{_repo_path(repository)}/git/blobs", blob_payload
        )
        if not isinstance(blob, Mapping):
            raise GitHubPublicationError(f"blob response missing for {change.path}")
        blob_sha = _require_sha(blob.get("sha"), f"blob_sha[{change.path}]")
        tree_elements.append(
            {
                "path": change.path,
                "mode": change.mode,
                "type": "blob",
                "sha": blob_sha,
            }
        )

    tree = transport.request(
        "POST",
        f"{_repo_path(repository)}/git/trees",
        {"base_tree": base_tree_sha, "tree": tree_elements},
    )
    if not isinstance(tree, Mapping):
        raise GitHubPublicationError("tree response missing")
    tree_sha = _require_sha(tree.get("sha"), "tree_sha")

    commit = transport.request(
        "POST",
        f"{_repo_path(repository)}/git/commits",
        {
            "message": str(contract.get("commit_message") or ""),
            "tree": tree_sha,
            "parents": [parent_sha],
        },
    )
    if not isinstance(commit, Mapping):
        raise GitHubPublicationError("commit response missing")
    commit_sha = _require_sha(commit.get("sha"), "commit_sha")

    base_ref_before_publish = transport.request(
        "GET", _git_ref_path(repository, base_branch)
    )
    if not isinstance(base_ref_before_publish, Mapping):
        raise GitHubPublicationError("base branch disappeared before publication")
    if _extract_ref_sha(base_ref_before_publish, "base_ref_before_publish") != expected_base_sha:
        raise GitHubPublicationError(
            "base branch moved while the atomic commit was being prepared"
        )

    if mode == "create":
        transport.request(
            "POST",
            f"{_repo_path(repository)}/git/refs",
            {"ref": f"refs/heads/{head_branch}", "sha": commit_sha},
        )
    else:
        transport.request(
            "PATCH",
            _git_ref_path(repository, head_branch).replace("/git/ref/", "/git/refs/"),
            {"sha": commit_sha, "force": False},
        )

    pr_payload = {
        "title": str(contract.get("pr_title") or ""),
        "head": head_branch,
        "base": base_branch,
        "body": str(private.get("pr_body") or ""),
        "draft": bool(contract.get("draft", True)),
        "maintainer_can_modify": True,
    }
    if mode == "create":
        pr = transport.request("POST", f"{_repo_path(repository)}/pulls", pr_payload)
    else:
        pr_number = contract.get("pr_number")
        if not isinstance(pr_number, int) or pr_number <= 0:
            raise GitHubPublicationError("update mode requires a positive pr_number")
        pr = transport.request(
            "PATCH",
            f"{_repo_path(repository)}/pulls/{pr_number}",
            {
                "title": pr_payload["title"],
                "body": pr_payload["body"],
                "base": base_branch,
                "state": "open",
                "maintainer_can_modify": True,
            },
        )
    if not isinstance(pr, Mapping):
        raise GitHubPublicationError("pull request response missing")

    receipt_core = {
        "version": GITHUB_PUBLICATION_VERSION,
        "contract_id": str(contract.get("contract_id") or ""),
        "repository_full_name": repository,
        "publication_mode": mode,
        "base_branch": base_branch,
        "base_sha": observed_base_sha,
        "parent_sha": parent_sha,
        "head_branch": head_branch,
        "commit_sha": commit_sha,
        "tree_sha": tree_sha,
        "pr_number": int(pr.get("number") or 0),
        "pr_url": str(pr.get("html_url") or ""),
        "force_ref_update": False,
        "atomic_commit": True,
        "automatic_merge": False,
        "human_review_required": True,
    }
    return {
        **receipt_core,
        "receipt_digest": _sha256(receipt_core),
        "ok": True,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def compile_merge_connector_packet(
    *,
    repository_full_name: str,
    pr_number: int,
    expected_head_sha: str,
    merge_method: str = "squash",
    human_merge_authorized: bool = False,
    checks_passed: bool = False,
    review_threads_resolved: bool = False,
    codemap_regenerated: bool = False,
) -> dict[str, Any]:
    """Prepare, but never execute, the exact guarded merge call."""

    repository = _normalize_repo(repository_full_name)
    expected = _require_sha(expected_head_sha, "expected_head_sha")
    if not isinstance(pr_number, int) or pr_number <= 0:
        raise GitHubPublicationError("pr_number must be a positive integer")
    if merge_method not in {"merge", "squash", "rebase"}:
        raise GitHubPublicationError("merge_method must be merge, squash, or rebase")

    gates = {
        "human_merge_authorized": human_merge_authorized is True,
        "checks_passed": checks_passed is True,
        "review_threads_resolved": review_threads_resolved is True,
        "codemap_regenerated": codemap_regenerated is True,
    }
    ready = all(gates.values())
    core = {
        "version": GITHUB_PUBLICATION_VERSION,
        "repository_full_name": repository,
        "pr_number": pr_number,
        "expected_head_sha": expected,
        "merge_method": merge_method,
        "gates": gates,
        "ready": ready,
        "automatic_merge": False,
        "human_review_required": True,
    }
    return {
        **core,
        "packet_id": f"GHMERGE-{_sha256(core)[:24]}",
        "connector_tool": "GitHub.merge_pull_request",
        "connector_arguments": {
            "repository_full_name": repository,
            "pr_number": pr_number,
            "merge_method": merge_method,
            "expected_head_sha": expected,
        }
        if ready
        else None,
        "status": "READY_FOR_EXPLICIT_MERGE" if ready else "BLOCKED",
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


class GitHubPublishingAuraAgentArenaBridge(PersistentAuraAgentArenaBridge):
    """Persistent Agent Bridge with guarded atomic GitHub publication tools."""

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
                repair_hint="Repair the exact GitHub publication request and retry.",
            )
        public = {key: value for key, value in contract.items() if key != "_private"}
        self._sessions.setdefault("github_publications", {})[contract["contract_id"]] = contract
        return {"ok": True, **public}

    def aura_github_execute_publication(
        self,
        *,
        contract_id: str,
    ) -> dict[str, Any]:
        contracts = self._sessions.get("github_publications", {})
        contract = contracts.get(str(contract_id or ""))
        if not isinstance(contract, Mapping):
            return make_error_packet(
                "missing_grounding",
                "Unknown GitHub publication contract.",
                repair_hint="Call aura_github_prepare_publication first in this process.",
            )
        token = os.environ.get("AURA_GITHUB_TOKEN", "")
        try:
            transport = GitHubRestTransport(token=token)
            return execute_publication_contract(contract, transport=transport)
        except GitHubPublicationError as exc:
            return make_error_packet(
                "test_failed",
                str(exc),
                repair_hint="Do not retry blindly; refresh exact refs and recompile the contract.",
            )

    def aura_github_prepare_merge(
        self,
        request_payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        try:
            return {
                "ok": True,
                **compile_merge_connector_packet(
                    repository_full_name=str(
                        request_payload.get("repository_full_name") or ""
                    ),
                    pr_number=int(request_payload.get("pr_number") or 0),
                    expected_head_sha=str(
                        request_payload.get("expected_head_sha") or ""
                    ),
                    merge_method=str(request_payload.get("merge_method", "squash")),
                    human_merge_authorized=request_payload.get(
                        "human_merge_authorized"
                    )
                    is True,
                    checks_passed=request_payload.get("checks_passed") is True,
                    review_threads_resolved=request_payload.get(
                        "review_threads_resolved"
                    )
                    is True,
                    codemap_regenerated=request_payload.get("codemap_regenerated")
                    is True,
                ),
            }
        except (GitHubPublicationError, TypeError, ValueError) as exc:
            return make_error_packet(
                "test_failed",
                str(exc),
                repair_hint="Satisfy every exact-head merge gate before requesting merge.",
            )

    @staticmethod
    def list_tools() -> list[dict[str, Any]]:
        return [
            *PersistentAuraAgentArenaBridge.list_tools(),
            {
                "name": "aura_github_prepare_publication",
                "description": "Compile an exact-head atomic GitHub branch/commit/PR contract.",
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
                "description": "Execute one explicitly authorized contract through the Git Data API; never merge.",
                "required_inputs": ["contract_id"],
            },
            {
                "name": "aura_github_prepare_merge",
                "description": "Prepare a separate exact-head connector merge packet after every human/review/CODEMAP gate passes.",
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
        "transport": "github_git_data_api",
        "atomic_commit": True,
        "temporary_workflow_transport": False,
        "automatic_merge": False,
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
