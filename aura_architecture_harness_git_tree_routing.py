"""Proposal-only GitHub atomic Git-tree routing for Aura's architecture harness.

The module records a deterministic publication plan for an external authorized
GitHub connector. It performs no GitHub mutation and grants no merge, force,
base-branch, production, or other consequential authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import PurePosixPath
import re
from typing import Any, Iterable, Mapping

VERSION = "AURA_ARCHITECTURE_HARNESS_GIT_TREE_ROUTING_V4"
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


def _sha1(value: str, name: str) -> str:
    if type(value) is not str or SHA1_PATTERN.fullmatch(value) is None:
        raise GitTreeRoutingError(f"{name} must be a lowercase 40-character Git SHA-1")
    return value


def _sha256(value: str, name: str) -> str:
    if type(value) is not str or SHA256_PATTERN.fullmatch(value) is None:
        raise GitTreeRoutingError(f"{name} must be a lowercase 64-character SHA-256")
    return value


@dataclass(frozen=True)
class VerifiedHeadBinding:
    """Commit/tree identity derived from one exact connector fetch-commit response."""

    commit_sha: str
    tree_sha: str
    verification_action: str = "fetch_commit"

    def __post_init__(self) -> None:
        _sha1(self.commit_sha, "commit_sha")
        _sha1(self.tree_sha, "tree_sha")
        if self.commit_sha == self.tree_sha:
            raise GitTreeRoutingError("tree_sha must be a tree object, not the commit SHA")
        if self.verification_action != "fetch_commit":
            raise GitTreeRoutingError("verification_action must be fetch_commit")

    @classmethod
    def from_fetch_commit(
        cls, *, expected_head_sha: str, commit_metadata: Mapping[str, Any]
    ) -> "VerifiedHeadBinding":
        """Derive a binding from one exact connector commit-metadata object."""

        expected = _sha1(expected_head_sha, "expected_head_sha")
        if not isinstance(commit_metadata, Mapping):
            raise GitTreeRoutingError("commit_metadata must be a mapping")
        observed = commit_metadata.get("sha")
        tree = commit_metadata.get("tree")
        tree_sha = tree.get("sha") if isinstance(tree, Mapping) else None
        if observed != expected:
            raise GitTreeRoutingError("commit metadata does not match expected_head_sha")
        return cls(commit_sha=expected, tree_sha=_sha1(tree_sha, "commit_metadata.tree.sha"))

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


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
    repository_full_name: str,
    pull_request_number: int,
    branch: str,
    head_binding: VerifiedHeadBinding,
    blobs: Iterable[GitTreeBlobIntent],
    deletions: Iterable[str] = (),
) -> dict[str, Any]:
    """Build a deterministic proposal bound to one verified commit/tree pair."""

    if (
        type(repository_full_name) is not str
        or REPOSITORY_PATTERN.fullmatch(repository_full_name) is None
    ):
        raise GitTreeRoutingError("repository_full_name must use owner/name form")
    if type(pull_request_number) is not int or pull_request_number < 1:
        raise GitTreeRoutingError("pull_request_number must be positive")
    if (
        type(branch) is not str
        or not branch
        or branch.startswith("refs/")
        or "\x00" in branch
    ):
        raise GitTreeRoutingError("branch must be a plain non-empty branch name")
    if type(head_binding) is not VerifiedHeadBinding:
        raise GitTreeRoutingError("head_binding must be a VerifiedHeadBinding")

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
        raise GitTreeRoutingError(
            f"paths cannot be replaced and deleted together: {overlap}"
        )

    identity = {
        "repository_full_name": repository_full_name,
        "pull_request_number": pull_request_number,
        "branch": branch,
        "head_binding": head_binding.to_dict(),
        "expected_head_sha": head_binding.commit_sha,
        "expected_head_tree_sha": head_binding.tree_sha,
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
            "the pull request is open and its head SHA equals head_binding.commit_sha",
            "head_binding was derived from one exact fetch_commit response",
            "the fetched commit tree equals head_binding.tree_sha",
            "all file bytes already passed the requested validation gate",
            "the replacement and deletion allowlists are exact and human-reviewed",
        ],
        "connector_sequence": [
            {
                "order": 1,
                "action": "get_pr_info",
                "assertions": ["open PR", "expected branch", "exact head commit"],
            },
            {
                "order": 2,
                "action": "fetch_commit",
                "commit_sha": head_binding.commit_sha,
                "expected_tree_sha": head_binding.tree_sha,
                "assertions": [
                    "commit remains the live PR head",
                    "commit tree equals the bound tree SHA",
                ],
            },
            {
                "order": 3,
                "action": "create_blob",
                "per_file": True,
                "assertions": ["exact bytes", "local SHA-256", "regular-file mode only"],
            },
            {
                "order": 4,
                "action": "create_tree",
                "base_tree_sha": head_binding.tree_sha,
                "assertions": [
                    "base tree is the bound tree object",
                    "tree contains the complete replacement/add/delete set",
                ],
            },
            {
                "order": 5,
                "action": "create_commit",
                "parent_sha": head_binding.commit_sha,
                "assertions": ["one parent", "one atomic tree", "reviewable message"],
            },
            {
                "order": 6,
                "action": "update_ref",
                "branch": branch,
                "force": False,
                "assertions": ["fast-forward only", "never update the base branch"],
            },
            {
                "order": 7,
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


def proven_pr184_route_record() -> dict[str, Any]:
    """Return the verified PR #184 manual-remediation publication case study."""

    placeholder = GitTreeBlobIntent(
        path="docs/AURA_ARCHITECTURE_HARNESS_GIT_TREE_ROUTING.md",
        content_sha256="0" * 64,
        byte_length=0,
    )
    binding = VerifiedHeadBinding.from_fetch_commit(
        expected_head_sha="7207c2bf6ab179d6af41ca4ed6b9f5adcce1b307",
        commit_metadata={
            "sha": "7207c2bf6ab179d6af41ca4ed6b9f5adcce1b307",
            "tree": {"sha": "359a19f26aa3f4066c51263965709c8b026eae6c"},
        },
    )
    record = build_git_tree_routing_record(
        repository_full_name="dallascourchene-commits/AuraOS",
        pull_request_number=184,
        branch="work/construction-arena-real-asset-pack-g4-20260722",
        head_binding=binding,
        blobs=(placeholder,),
        deletions=(
            ".github/workflows/apply-pr184-g4-adapter.yml",
            ".github/workflows/construction-demo-documentation-sync.yml",
            ".github/workflows/construction-demo-ifc-proof.yml",
            ".github/workflows/construction-demo-spz-build-diagnostics.yml",
            ".github/workflows/construction-demo-toolchain-diagnostics.yml",
            ".github/workflows/pr184-review-remediation.yml",
        ),
    )
    record["case_study"] = {
        "recorded_at": "2026-07-22",
        "scope": "manual review remediation publication, not G4 payload cleanup",
        "outcome": "atomic Git-tree publication succeeded on the live PR branch",
        "resolved_head_tree_sha": binding.tree_sha,
        "created_tree_sha": "beed4f512975dd304ff36aa7e2936bf2212cead1",
        "created_commit_sha": "ea9675ada226bae31fbd74e10dced81797aac1a8",
        "base_tree_is_commit_sha": False,
        "confirmed_force_required": False,
        "note": "The placeholder blob documents routing shape, not a publication request.",
    }
    return record
