"""Proposal-only GitHub atomic Git-tree routing for Aura's architecture harness.

Records emitted here are untrusted plans. The executing GitHub connector must
independently re-fetch the live pull request and head commit before creating
objects and again before moving a ref. This module performs no remote mutation
and grants no merge, force, base-branch, production, or other consequential
authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import PurePosixPath
import re
from typing import Any, Iterable, Mapping
import unicodedata

VERSION = "AURA_ARCHITECTURE_HARNESS_GIT_TREE_ROUTING_V5"
SHA1_PATTERN = re.compile(r"^[0-9a-f]{40}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_BINDING_FACTORY_TOKEN = object()

AUTHORITY_CONTRACT = {
    "production_mutation": False,
    "automatic_blob_creation": False,
    "automatic_tree_creation": False,
    "automatic_commit": False,
    "automatic_ref_update": False,
    "force_ref_update": False,
    "automatic_pull_request": False,
    "automatic_merge": False,
    "base_branch_update_authorized": False,
    "human_review_required": True,
    "execution_requires_external_authorized_connector": True,
}

WORKFLOW_DISCOVERY = {
    "pull_request_definition_source": "base_branch",
    "branch_new_pull_request_workflow_jobs_reliable": False,
    "reason": (
        "GitHub evaluates pull_request workflow definitions from the trusted base "
        "branch. New or materially rewritten jobs that exist only on a PR branch "
        "must not be relied on to publish that PR's source changes."
    ),
    "commit_workflow_lookup_scope": "pull_request_triggered_first_page",
    "connector_visibility_limit": (
        "The connector workflow-run lookup used during PR #184 exposed "
        "pull-request-triggered runs but did not reliably expose branch push runs."
    ),
    "contents_api_partial_state_risk": (
        "Sequential Contents-API writes create one commit per path and can expose an "
        "intermediate partial source state."
    ),
    "preferred_fallback": "atomic_git_object_route",
}


class GitTreeRoutingError(ValueError):
    """Raised when an atomic publication proposal is non-canonical or unsafe."""


def _canonical_repo_path(value: str) -> str:
    if type(value) is not str or not value or "\\" in value or "\x00" in value:
        raise GitTreeRoutingError(f"unsafe repository path: {value!r}")
    if re.match(r"^[A-Za-z]:", value):
        raise GitTreeRoutingError(f"Windows drive path is not allowed: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise GitTreeRoutingError(f"unsafe repository path: {value!r}")
    normalized = path.as_posix()
    if normalized != value:
        raise GitTreeRoutingError(f"non-canonical repository path: {value!r}")
    return normalized


def _portable_path_key(value: str) -> tuple[str, ...]:
    """Return a conservative cross-platform collision key for a repository path."""

    canonical = _canonical_repo_path(value)
    return tuple(
        unicodedata.normalize("NFC", part).casefold()
        for part in PurePosixPath(canonical).parts
    )


def _reject_portable_path_collisions(paths: Iterable[str]) -> None:
    """Reject case/Unicode aliases and file-versus-descendant tree conflicts."""

    originals: dict[tuple[str, ...], str] = {}
    ordered = tuple(paths)
    for value in ordered:
        key = _portable_path_key(value)
        previous = originals.get(key)
        if previous is not None and previous != value:
            raise GitTreeRoutingError(
                f"repository paths collide on common filesystems: {previous!r}, {value!r}"
            )
        originals[key] = value
    keys = set(originals)
    for key, value in originals.items():
        for length in range(1, len(key)):
            ancestor = key[:length]
            if ancestor in keys:
                raise GitTreeRoutingError(
                    "repository path cannot be both a file and an ancestor of another "
                    f"path: {originals[ancestor]!r}, {value!r}"
                )


def _sha1(value: str, name: str) -> str:
    if type(value) is not str or SHA1_PATTERN.fullmatch(value) is None:
        raise GitTreeRoutingError(f"{name} must be a lowercase 40-character Git SHA-1")
    return value


def _sha256(value: str, name: str) -> str:
    if type(value) is not str or SHA256_PATTERN.fullmatch(value) is None:
        raise GitTreeRoutingError(f"{name} must be a lowercase 64-character SHA-256")
    return value


@dataclass(frozen=True, init=False)
class PullRequestRouteBinding:
    """Opaque proposal identity derived from one PR response and one commit response.

    This is not an authentication capability. Even a factory-created instance is
    untrusted proposal data; the executing connector must independently re-fetch
    and compare every field before creating blobs and before updating the ref.
    """

    repository_full_name: str
    pull_request_number: int
    state: str
    merged: bool
    head_branch: str
    base_branch: str
    head_sha: str
    tree_sha: str
    metadata_sources: tuple[str, str]
    _factory_token: object = field(repr=False, compare=False)

    @classmethod
    def from_connector_metadata(
        cls,
        *,
        repository_full_name: str,
        pull_request_metadata: Mapping[str, Any],
        commit_metadata: Mapping[str, Any],
    ) -> "PullRequestRouteBinding":
        """Derive a proposal binding from normalized connector metadata."""

        if (
            type(repository_full_name) is not str
            or REPOSITORY_PATTERN.fullmatch(repository_full_name) is None
        ):
            raise GitTreeRoutingError("repository_full_name must use owner/name form")
        if not isinstance(pull_request_metadata, Mapping):
            raise GitTreeRoutingError("pull_request_metadata must be a mapping")
        if not isinstance(commit_metadata, Mapping):
            raise GitTreeRoutingError("commit_metadata must be a mapping")

        number = pull_request_metadata.get("number")
        state = pull_request_metadata.get("state")
        merged = pull_request_metadata.get("merged")
        head_branch = pull_request_metadata.get("head")
        base_branch = pull_request_metadata.get("base")
        head_sha = pull_request_metadata.get("head_sha")
        if type(number) is not int or number < 1:
            raise GitTreeRoutingError("pull request number must be positive")
        if state != "open" or merged is not False:
            raise GitTreeRoutingError("pull request must be open and unmerged")
        for name, value in (("head branch", head_branch), ("base branch", base_branch)):
            if (
                type(value) is not str
                or not value
                or value.startswith("refs/")
                or "\x00" in value
            ):
                raise GitTreeRoutingError(f"{name} must be a plain non-empty branch")
        if head_branch == base_branch:
            raise GitTreeRoutingError("pull request head branch must differ from base branch")

        expected_head = _sha1(head_sha, "pull_request_metadata.head_sha")
        observed_head = _sha1(commit_metadata.get("sha"), "commit_metadata.sha")
        tree = commit_metadata.get("tree")
        tree_sha = tree.get("sha") if isinstance(tree, Mapping) else None
        resolved_tree = _sha1(tree_sha, "commit_metadata.tree.sha")
        if observed_head != expected_head:
            raise GitTreeRoutingError(
                "commit metadata does not match the pull request head SHA"
            )
        if resolved_tree == expected_head:
            raise GitTreeRoutingError("tree SHA must be a tree object, not the commit SHA")

        instance = object.__new__(cls)
        values = {
            "repository_full_name": repository_full_name,
            "pull_request_number": number,
            "state": state,
            "merged": merged,
            "head_branch": head_branch,
            "base_branch": base_branch,
            "head_sha": expected_head,
            "tree_sha": resolved_tree,
            "metadata_sources": ("get_pr_info", "fetch_commit"),
            "_factory_token": _BINDING_FACTORY_TOKEN,
        }
        for name, value in values.items():
            object.__setattr__(instance, name, value)
        return instance

    def to_dict(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in asdict(self).items()
            if key != "_factory_token"
        }


@dataclass(frozen=True)
class GitTreeBlobIntent:
    """One exact regular-file addition or replacement admitted to an atomic tree."""

    path: str
    content_sha256: str
    byte_length: int
    mode: str = "100644"
    object_type: str = "blob"

    def __post_init__(self) -> None:
        _canonical_repo_path(self.path)
        _sha256(self.content_sha256, "content_sha256")
        if type(self.byte_length) is not int or self.byte_length < 0:
            raise GitTreeRoutingError("byte_length must be a non-negative integer")
        if self.mode not in {"100644", "100755"}:
            raise GitTreeRoutingError("only regular-file Git modes are admitted")
        if self.object_type != "blob":
            raise GitTreeRoutingError("object_type must be blob")

    @classmethod
    def from_bytes(
        cls, path: str, content: bytes, *, executable: bool = False
    ) -> "GitTreeBlobIntent":
        if type(content) is not bytes:
            raise GitTreeRoutingError("content must be exact bytes")
        return cls(
            path=_canonical_repo_path(path),
            content_sha256=hashlib.sha256(content).hexdigest(),
            byte_length=len(content),
            mode="100755" if executable else "100644",
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_git_tree_routing_record(
    *,
    binding: PullRequestRouteBinding,
    blobs: Iterable[GitTreeBlobIntent] = (),
    deletions: Iterable[str] = (),
) -> dict[str, Any]:
    """Build an untrusted deterministic proposal for an atomic publication."""

    if (
        type(binding) is not PullRequestRouteBinding
        or getattr(binding, "_factory_token", None) is not _BINDING_FACTORY_TOKEN
    ):
        raise GitTreeRoutingError(
            "binding must be factory-created from connector metadata"
        )

    blob_rows = tuple(sorted(tuple(blobs), key=lambda item: item.path))
    if not all(type(item) is GitTreeBlobIntent for item in blob_rows):
        raise GitTreeRoutingError("blobs must contain exact GitTreeBlobIntent values")
    blob_paths = tuple(item.path for item in blob_rows)
    if len(blob_paths) != len(set(blob_paths)):
        raise GitTreeRoutingError("blob paths must be unique")

    deletion_paths = tuple(sorted(_canonical_repo_path(item) for item in deletions))
    if len(deletion_paths) != len(set(deletion_paths)):
        raise GitTreeRoutingError("deletion paths must be unique")
    if not blob_rows and not deletion_paths:
        raise GitTreeRoutingError("route must add, replace, or delete at least one path")
    overlap = sorted(set(blob_paths) & set(deletion_paths))
    if overlap:
        raise GitTreeRoutingError(
            f"paths cannot be replaced and deleted together: {overlap}"
        )
    _reject_portable_path_collisions((*blob_paths, *deletion_paths))

    identity = {
        "binding": binding.to_dict(),
        "blob_intents": [item.to_dict() for item in blob_rows],
        "deletions": list(deletion_paths),
    }
    route_digest = hashlib.blake2b(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8"),
        digest_size=16,
    ).hexdigest()
    return {
        "version": VERSION,
        "record_kind": "UNTRUSTED_ATOMIC_PUBLICATION_PROPOSAL",
        "route_digest": route_digest,
        **identity,
        "executor_must_independently_refetch": True,
        "preconditions": [
            "the executing connector independently re-fetches this exact repository and PR",
            "the live PR is open, unmerged, and has the bound non-base head branch",
            "the live PR head SHA equals binding.head_sha",
            "a fresh fetch_commit(binding.head_sha) resolves exactly binding.tree_sha",
            "all file bytes already passed the requested validation gate",
            "the replacement and deletion allowlists are exact and human-reviewed",
        ],
        "connector_sequence": [
            {
                "order": 1,
                "action": "get_pr_info",
                "assertions": [
                    "repository and PR number equal the binding",
                    "open and unmerged",
                    "head ref equals binding.head_branch",
                    "base ref equals binding.base_branch",
                    "head and base refs differ",
                    "head SHA equals binding.head_sha",
                ],
            },
            {
                "order": 2,
                "action": "fetch_commit",
                "commit_sha": binding.head_sha,
                "expected_tree_sha": binding.tree_sha,
                "assertions": ["commit SHA and tree SHA equal the binding"],
            },
            {
                "order": 3,
                "action": "create_blob",
                "per_file": True,
                "skip_when_no_blob_intents": True,
                "assertions": ["exact bytes", "local SHA-256", "regular-file mode only"],
            },
            {
                "order": 4,
                "action": "create_tree",
                "base_tree_sha": binding.tree_sha,
                "assertions": [
                    "base tree is the independently re-fetched tree object",
                    "tree contains the complete replacement/add/delete set",
                ],
            },
            {
                "order": 5,
                "action": "create_commit",
                "parent_sha": binding.head_sha,
                "assertions": ["one parent", "one atomic tree", "reviewable message"],
            },
            {
                "order": 6,
                "action": "get_pr_info",
                "purpose": "stale-head and branch revalidation immediately before ref update",
                "assertions": [
                    "same repository and PR",
                    "same non-base head branch",
                    "head SHA still equals binding.head_sha",
                ],
            },
            {
                "order": 7,
                "action": "update_ref",
                "branch": binding.head_branch,
                "force": False,
                "assertions": [
                    "fast-forward only",
                    "target is the verified PR head branch",
                    "target is not binding.base_branch",
                ],
            },
            {
                "order": 8,
                "action": "verify",
                "assertions": [
                    "PR head equals the created commit",
                    "changed filenames equal the intended allowlist",
                    "every path listed in deletions is absent",
                    "tests and generated-map verification pass on the final tree",
                    "PR remains unmerged unless separately authorized",
                ],
            },
        ],
        "workflow_discovery": dict(WORKFLOW_DISCOVERY),
        "why_atomic": (
            "All immutable blobs are prepared before one tree and one commit become "
            "reachable through a non-forced fast-forward."
        ),
        "rollback": {
            "before_update_ref": "discard unattached objects; the branch remains unchanged",
            "after_update_ref": "create a reviewed revert; never force rewind",
        },
        "authority": dict(AUTHORITY_CONTRACT),
    }


def pr184_atomic_publication_case_study() -> dict[str, Any]:
    """Return historical PR #184 facts, explicitly not a replayable route receipt."""

    return {
        "version": VERSION,
        "record_kind": "HISTORICAL_NON_REPLAYABLE_CASE_STUDY",
        "replayable_route": False,
        "status": "PROPOSAL_ONLY_EXTERNAL_CONNECTOR_REQUIRED",
        "workflow_discovery": dict(WORKFLOW_DISCOVERY),
        "connector_sequence": [
            "get_pr_info",
            "fetch_commit",
            "create_blob",
            "create_tree",
            "create_commit",
            "get_pr_info",
            "update_ref(force=false)",
            "verify",
        ],
        "preconditions": [
            "independently re-fetch live PR and commit metadata",
            "bind repository, PR number, head ref, base ref, head SHA, and tree SHA",
            "never target the base ref",
        ],
        "rollback": {
            "before_update_ref": "discard unattached objects",
            "after_update_ref": "reviewed revert only; never force rewind",
        },
        "case_study": {
            "recorded_at": "2026-07-22",
            "scope": "manual review-remediation publication, not G4 payload cleanup",
            "outcome": "atomic Git-tree publication succeeded on the live PR branch",
            "parent_commit_sha": "7207c2bf6ab179d6af41ca4ed6b9f5adcce1b307",
            "resolved_parent_tree_sha": "359a19f26aa3f4066c51263965709c8b026eae6c",
            "created_tree_sha": "beed4f512975dd304ff36aa7e2936bf2212cead1",
            "created_commit_sha": "ea9675ada226bae31fbd74e10dced81797aac1a8",
            "actual_blob_intents_recorded": False,
            "route_digest_is_provenance_receipt": False,
            "confirmed_force_required": False,
            "note": (
                "This record preserves independently checked historical object IDs only. "
                "It intentionally contains no synthetic placeholder blob or route digest."
            ),
        },
        "authority": dict(AUTHORITY_CONTRACT),
    }
