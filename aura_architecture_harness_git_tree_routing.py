"""Proposal-only GitHub atomic Git-tree routing record for Aura's architecture harness.

This companion records how an external coding agent can publish an already validated,
allowlisted multi-file change to an existing pull-request branch without producing a
sequence of partial Contents-API commits.  It does not call GitHub, move refs, push,
merge, or grant mutation authority by itself.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import PurePosixPath
import re
from typing import Any, Iterable

VERSION = "AURA_ARCHITECTURE_HARNESS_GIT_TREE_ROUTING_V1"
SHA1_PATTERN = re.compile(r"^[0-9a-f]{40}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")

AUTHORITY_CONTRACT = {
    "production_mutation": False,
    "automatic_blob_creation": False,
    "automatic_tree_creation": False,
    "automatic_commit": False,
    "automatic_ref_update": False,
    "force_ref_update": False,
    "automatic_pull_request": False,
    "automatic_merge": False,
    "human_review_required": True,
    "execution_requires_external_authorized_connector": True,
}

WORKFLOW_DISCOVERY = {
    "pull_request_definition_source": "base_branch",
    "branch_new_pull_request_workflow_jobs_reliable": False,
    "reason": (
        "GitHub evaluates pull_request workflow definitions from the base branch, so "
        "new or materially rewritten workflow jobs that exist only on the PR branch "
        "may not execute for that PR."
    ),
    "connector_visibility_limit": (
        "The commit-workflow lookup used during PR #184 exposed pull-request-triggered "
        "runs but did not reliably expose branch push runs."
    ),
    "preferred_fallback": "atomic_git_object_route",
}


class GitTreeRoutingError(ValueError):
    """Raised when a proposed atomic publication route is not canonical or safe."""


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


def _sha1(value: str, name: str) -> str:
    if type(value) is not str or SHA1_PATTERN.fullmatch(value) is None:
        raise GitTreeRoutingError(f"{name} must be a lowercase 40-character Git SHA-1")
    return value


def _sha256(value: str, name: str) -> str:
    if type(value) is not str or SHA256_PATTERN.fullmatch(value) is None:
        raise GitTreeRoutingError(f"{name} must be a lowercase 64-character SHA-256")
    return value


@dataclass(frozen=True)
class GitTreeBlobIntent:
    """One exact file replacement/addition admitted to the atomic tree."""

    path: str
    content_sha256: str
    byte_length: int
    mode: str = "100644"
    object_type: str = "blob"

    def __post_init__(self) -> None:
        if self.path != _canonical_repo_path(self.path):
            raise GitTreeRoutingError("path must be canonical")
        if self.content_sha256 != _sha256(self.content_sha256, "content_sha256"):
            raise GitTreeRoutingError("content_sha256 must be canonical")
        if type(self.byte_length) is not int or self.byte_length < 0:
            raise GitTreeRoutingError("byte_length must be a non-negative integer")
        if self.mode not in {"100644", "100755"}:
            raise GitTreeRoutingError("only regular-file Git modes are admitted")
        if self.object_type != "blob":
            raise GitTreeRoutingError("object_type must be blob")

    @classmethod
    def from_bytes(cls, path: str, content: bytes, *, executable: bool = False) -> "GitTreeBlobIntent":
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
    repository_full_name: str,
    pull_request_number: int,
    branch: str,
    expected_head_sha: str,
    blobs: Iterable[GitTreeBlobIntent],
    deletions: Iterable[str] = (),
) -> dict[str, Any]:
    """Build a deterministic, proposal-only atomic publication receipt.

    The returned sequence mirrors the successfully proven route used on AuraOS PR #184:
    resolve the exact PR head, create immutable blobs, create one tree rooted at that
    head, create one single-parent commit, then fast-forward the PR branch with force
    disabled and verify the resulting head and diff.
    """

    if type(repository_full_name) is not str or REPOSITORY_PATTERN.fullmatch(repository_full_name) is None:
        raise GitTreeRoutingError("repository_full_name must use owner/name form")
    if type(pull_request_number) is not int or pull_request_number < 1:
        raise GitTreeRoutingError("pull_request_number must be positive")
    if type(branch) is not str or not branch or branch.startswith("refs/") or "\x00" in branch:
        raise GitTreeRoutingError,"branch must be a plain non-empty branch name")
    head = _sha1(expected_head_sha, "expected_head_sha")
    blob_rows = tuple(sorted(tuple(blobs), key=lambda item: item.path))
    if not blob_rows or not all(type(item) is GitTreeBlobIntent for item in blob_rows):
        raise GitTreeRoutingError("blobs must contain exact GitTreeBlobIntent values")
    blob_paths = tuple(item.path for item in blob_rows)
    if len(blob_paths) != len(set(blob_paths)):
        raise GitTreeRoutingError("blob paths must be unique")
    deletion_paths = tuple(sorted(_canonical_repo_path(item) for item in deletions))
    if len(deletion_paths) != len(set(deletion_paths)):
        raise GitTreeRoutingError("deletion paths must be unique")
    overlap = sorted(set(blob_paths) & set(deletion_paths))
    if overlap:
        raise GitTreeRoutingError(f"paths cannot be replaced and deleted together: {overlap}")

    identity = {
        "repository_full_name": repository_full_name,
        "pull_request_number": pull_request_number,
        "branch": branch,
        "expected_head_sha": head,
        "blob_intents": [item.to_dict() for item in blob_rows],
        "deletions": list(deletion_paths),
    }
    route_digest = hashlib.blake2b(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8"),
        digest_size=16,
    ).hexdigest()
    return {
        "version": VERSION,
        "route_digest": route_digest,
        **identity,
        "preconditions": [
            "the pull request is open and its head SHA exactly equals expected_head_sha",
            "all file bytes have already passed the requested validation gate",
            "the path allowlist and deletion allowlist are exact and human-reviewed",
            "generated navigation artifacts are regenerated from the final source tree",
        ],
        "connector_sequence": [
            {
                "order": 1,
                "action": "get_pr_info",
                "assertions": ["open PR", "expected branch", "exact expected_head_sha"],
            },
            {
                "order": 2,
                "action": "create_blob",
                "per_file": True,
                "assertions": ["exact bytes", "local SHA-256", "regular-file mode only"],
            },
            {
                "order": 3,
                "action": "create_tree",
                "base_tree_sha": head,
                "assertions": [
                    "base tree is the exact current PR head",
                    "tree contains the complete replacement/add/delete set",
                    "temporary payload and workflow cleanup is included in the same tree",
                ],
            },
            {
                "order": 4,
                "action": "create_commit",
                "parent_sha": head,
                "assertions": ["one parent", "one atomic tree", "reviewable commit message"],
            },
            {
                "order": 5,
                "action": "update_ref",
                "branch": branch,
                "force": False,
                "assertions": ["fast-forward only", "never update the base branch"],
            },
            {
                "order": 6,
                "action": "verify",
                "assertions": [
                    "PR head equals the created commit",
                    "changed filenames equal the intended allowlist",
                    "temporary transport files are absent",
                    "tests and CODEMAP verification pass on the final tree",
                    "PR remains unmerged unless separately authorized",
                ],
            },
        ],
        "workflow_discovery": dict(WORKFLOW_DISCOVERY),
        "why_atomic": (
            "GitHub's Contents API creates one commit per file update; the Git-object route "
            "creates all blobs first and exposes them only through one tree, one commit, and "
            "one fast-forward ref update, preventing an observable partial source state."
        ),
        "rollback": {
            "before_update_ref": "discard unattached blobs/tree/commit; the branch is unchanged",
            "after_update_ref": "create a reviewed revert or a new corrective atomic commit; never force rewind",
        },
        "authority": dict(AUTHORITY_CONTRACT),
    }


def proven_pr184_route_record() -> dict[str, Any]:
    """Return the reusable case-study record derived from AuraOS PR #184."""

    placeholder = GitTreeBlobIntent(
        path="docs/AURA_ARCHITECTURE_HARNESS_GIT_TREE_ROUTING.md",
        content_sha256="0" * 64,
        byte_length=0,
    )
    record = build_git_tree_routing_record(
        repository_full_name="dallascourchene-commits/AuraOS",
        pull_request_number=184,
        branch="work/construction-arena-real-asset-pack-g4-20260722",
        expected_head_sha="e67d6bdf96e6ba909846295ff9f5fd50d87697e4",
        blobs=(placeholder,),
        deletions=(".aura/pr184-g4-adapter/READY",),
    )
    record["case_study"] = {
        "recorded_at": "2026-07-22",
        "outcome": "atomic Git tree creation was confirmed against the live PR head",
        "confirmed_base_tree_accepts_commit_sha": True,
        "confirmed_force_required": False,
        "note": "The placeholder blob documents the routing shape, not a publication request.",
    }
    return record


def main() -> int:
    print(json.dumps(proven_pr184_route_record(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
