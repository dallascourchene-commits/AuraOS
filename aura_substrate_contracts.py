"""Immutable P9 contracts for the public Aura cognitive-substrate manifest."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
from pathlib import PurePosixPath
import re
from typing import Any

from aura_event_contracts import canonical_json

SUBSTRATE_MANIFEST_VERSION = "AURA_SUBSTRATE_MANIFEST_P9_V1"
SUBSTRATE_RELEASE_INDEX_VERSION = "AURA_SUBSTRATE_RELEASE_INDEX_P9_V1"
SUBSTRATE_VERIFIER_VERSION = "AURA_SUBSTRATE_VERIFIER_P9_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_DRIVE = re.compile(r"^[A-Za-z]:")


class FileRole(str, Enum):
    CANONICAL_CONTRACT = "CANONICAL_CONTRACT"
    READ_ONLY_PROJECTOR = "READ_ONLY_PROJECTOR"
    COMPATIBILITY_FACADE = "COMPATIBILITY_FACADE"
    DOMAIN_SHADOW = "DOMAIN_SHADOW"
    INTEGRITY_HELPER = "INTEGRITY_HELPER"
    PUBLIC_DOCUMENTATION = "PUBLIC_DOCUMENTATION"
    RELEASE_TOOLING = "RELEASE_TOOLING"


class ContractStatus(str, Enum):
    CANONICAL = "CANONICAL"
    CANONICAL_EXTENSION = "CANONICAL_EXTENSION"
    READ_ONLY_PROJECTION = "READ_ONLY_PROJECTION"
    VERIFIED_COMPATIBILITY = "VERIFIED_COMPATIBILITY"
    VERIFIED_SHADOW = "VERIFIED_SHADOW"


class CompatibilityMode(str, Enum):
    ADDITIVE = "ADDITIVE"
    READ_ONLY = "READ_ONLY"
    SHADOW_ONLY = "SHADOW_ONLY"
    OPT_IN_COMPATIBILITY = "OPT_IN_COMPATIBILITY"
    RETAINED_LEGACY_DUAL_READ = "RETAINED_LEGACY_DUAL_READ"


class MigrationStatus(str, Enum):
    CANONICAL_CONTRACT_ADOPTED = "CANONICAL_CONTRACT_ADOPTED"
    CANONICAL_PROJECTION_ADOPTED = "CANONICAL_PROJECTION_ADOPTED"
    LEGACY_OWNER_RETAINED = "LEGACY_OWNER_RETAINED"
    LIVE_OWNER_RETAINED = "LIVE_OWNER_RETAINED"


def _text(value: Any, name: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _path(value: Any, name: str = "path") -> str:
    text = _text(value, name)
    pure = PurePosixPath(text)
    if (
        "\\" in text
        or text.startswith("/")
        or _DRIVE.match(text)
        or pure.as_posix() != text
        or any(part in {"", ".", ".."} for part in pure.parts)
    ):
        raise ValueError(f"{name} must be a normalized repository-relative path")
    return text


def _tuple_text(values: Any, name: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    if type(values) is not tuple:
        raise ValueError(f"{name} must be a tuple")
    result = tuple(_text(item, f"{name}[]") for item in values)
    if not allow_empty and not result:
        raise ValueError(f"{name} must not be empty")
    if len(result) != len(set(result)):
        raise ValueError(f"{name} must not contain duplicates")
    return result


def _pairs(values: Any, name: str) -> tuple[tuple[str, str], ...]:
    if type(values) is not tuple:
        raise ValueError(f"{name} must be a tuple")
    result: list[tuple[str, str]] = []
    for item in values:
        if type(item) is not tuple or len(item) != 2:
            raise ValueError(f"{name} entries must be pairs")
        result.append((_text(item[0], f"{name}.name"), _text(item[1], f"{name}.value")))
    names = [item[0] for item in result]
    if len(names) != len(set(names)):
        raise ValueError(f"{name} names must be unique")
    return tuple(result)


@dataclass(frozen=True)
class SubstrateFileRecord:
    path: str
    role: FileRole | str
    phase_ids: tuple[str, ...]
    public_symbols: tuple[str, ...] = ()
    version_bindings: tuple[tuple[str, str], ...] = ()
    expected_git_blob_sha1: str | None = None
    release_included: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", _path(self.path))
        if not isinstance(self.role, FileRole):
            object.__setattr__(self, "role", FileRole(str(self.role)))
        object.__setattr__(self, "phase_ids", _tuple_text(self.phase_ids, "phase_ids"))
        object.__setattr__(self, "public_symbols", _tuple_text(self.public_symbols, "public_symbols"))
        object.__setattr__(self, "version_bindings", _pairs(self.version_bindings, "version_bindings"))
        if self.expected_git_blob_sha1 is not None:
            if type(self.expected_git_blob_sha1) is not str or not _HEX40.fullmatch(self.expected_git_blob_sha1):
                raise ValueError("expected_git_blob_sha1 must be a lowercase Git blob SHA-1")
        if type(self.release_included) is not bool:
            raise ValueError("release_included must be a boolean")
        if self.role is FileRole.PUBLIC_DOCUMENTATION and not self.path.startswith("docs/"):
            raise ValueError("public documentation must live under docs/")
        if self.role is not FileRole.PUBLIC_DOCUMENTATION and self.path.endswith(".md"):
            raise ValueError("markdown release files must be classified as documentation")

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "role": self.role.value,
            "phase_ids": list(self.phase_ids),
            "public_symbols": list(self.public_symbols),
            "version_bindings": [
                {"name": name, "value": value} for name, value in self.version_bindings
            ],
            "expected_git_blob_sha1": self.expected_git_blob_sha1,
            "release_included": self.release_included,
        }


@dataclass(frozen=True)
class PhaseDisposition:
    phase_id: str
    title: str
    source_pr: int
    merge_commit: str
    component_paths: tuple[str, ...]
    dependencies: tuple[str, ...]
    evidence_paths: tuple[str, ...]
    retained_dependency_paths: tuple[str, ...]
    contract_status: ContractStatus | str
    compatibility_mode: CompatibilityMode | str
    migration_status: MigrationStatus | str
    live_owner: str
    ownership_disposition: str
    live_owner_changed: bool = False
    callers_redirected: bool = False
    store_transferred: bool = False
    history_backfilled: bool = False
    legacy_deleted: bool = False
    execution_authority_granted: bool = False
    publication_performed: bool = False
    private_reasoning_exported: bool = False
    patch_authority: str = PATCH_AUTHORITY

    def __post_init__(self) -> None:
        object.__setattr__(self, "phase_id", _text(self.phase_id, "phase_id"))
        object.__setattr__(self, "title", _text(self.title, "title"))
        if type(self.source_pr) is not int or self.source_pr < 1:
            raise ValueError("source_pr must be a positive integer")
        if type(self.merge_commit) is not str or not _COMMIT.fullmatch(self.merge_commit):
            raise ValueError("merge_commit must be a lowercase 40-character commit")
        object.__setattr__(
            self,
            "component_paths",
            tuple(
                _path(item, "component_paths[]")
                for item in _tuple_text(self.component_paths, "component_paths", allow_empty=False)
            ),
        )
        object.__setattr__(self, "dependencies", _tuple_text(self.dependencies, "dependencies"))
        object.__setattr__(
            self,
            "evidence_paths",
            tuple(
                _path(item, "evidence_paths[]")
                for item in _tuple_text(self.evidence_paths, "evidence_paths", allow_empty=False)
            ),
        )
        object.__setattr__(
            self,
            "retained_dependency_paths",
            tuple(
                _path(item, "retained_dependency_paths[]")
                for item in _tuple_text(self.retained_dependency_paths, "retained_dependency_paths")
            ),
        )
        for field_name, enum_type in (
            ("contract_status", ContractStatus),
            ("compatibility_mode", CompatibilityMode),
            ("migration_status", MigrationStatus),
        ):
            value = getattr(self, field_name)
            if not isinstance(value, enum_type):
                object.__setattr__(self, field_name, enum_type(str(value)))
        object.__setattr__(self, "live_owner", _text(self.live_owner, "live_owner"))
        object.__setattr__(
            self,
            "ownership_disposition",
            _text(self.ownership_disposition, "ownership_disposition"),
        )
        boundary_flags = (
            self.live_owner_changed,
            self.callers_redirected,
            self.store_transferred,
            self.history_backfilled,
            self.legacy_deleted,
            self.execution_authority_granted,
            self.publication_performed,
            self.private_reasoning_exported,
        )
        if any(type(value) is not bool for value in boundary_flags):
            raise ValueError("phase boundary flags must be booleans")
        if any(boundary_flags):
            raise ValueError("P9 phase ledger cannot claim migration or authority expansion")
        if self.patch_authority != PATCH_AUTHORITY:
            raise ValueError("phase patch authority boundary changed")

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase_id": self.phase_id,
            "title": self.title,
            "source_pr": self.source_pr,
            "merge_commit": self.merge_commit,
            "component_paths": list(self.component_paths),
            "dependencies": list(self.dependencies),
            "evidence_paths": list(self.evidence_paths),
            "retained_dependency_paths": list(self.retained_dependency_paths),
            "contract_status": self.contract_status.value,
            "compatibility_mode": self.compatibility_mode.value,
            "migration_status": self.migration_status.value,
            "live_owner": self.live_owner,
            "ownership_disposition": self.ownership_disposition,
            "live_owner_changed": False,
            "callers_redirected": False,
            "store_transferred": False,
            "history_backfilled": False,
            "legacy_deleted": False,
            "execution_authority_granted": False,
            "publication_performed": False,
            "private_reasoning_exported": False,
            "patch_authority": self.patch_authority,
        }


@dataclass(frozen=True)
class SubstrateManifest:
    files: tuple[SubstrateFileRecord, ...]
    phases: tuple[PhaseDisposition, ...]
    retained_external_surfaces: tuple[str, ...] = ()
    version: str = SUBSTRATE_MANIFEST_VERSION
    release_index_version: str = SUBSTRATE_RELEASE_INDEX_VERSION
    verifier_version: str = SUBSTRATE_VERIFIER_VERSION
    generated_topology_authoritative: bool = False
    package_published: bool = False

    def __post_init__(self) -> None:
        if self.version != SUBSTRATE_MANIFEST_VERSION:
            raise ValueError("unsupported substrate manifest version")
        if self.release_index_version != SUBSTRATE_RELEASE_INDEX_VERSION:
            raise ValueError("unsupported release index version")
        if self.verifier_version != SUBSTRATE_VERIFIER_VERSION:
            raise ValueError("unsupported verifier version")
        if type(self.files) is not tuple or not self.files or not all(isinstance(item, SubstrateFileRecord) for item in self.files):
            raise ValueError("files must be a non-empty tuple of SubstrateFileRecord")
        if type(self.phases) is not tuple or not self.phases or not all(isinstance(item, PhaseDisposition) for item in self.phases):
            raise ValueError("phases must be a non-empty tuple of PhaseDisposition")
        paths = tuple(item.path for item in self.files)
        if paths != tuple(sorted(set(paths))):
            raise ValueError("manifest file paths must be unique and sorted")
        phase_ids = tuple(item.phase_id for item in self.phases)
        if len(phase_ids) != len(set(phase_ids)):
            raise ValueError("phase IDs must be unique")
        external = tuple(
            _path(item, "retained_external_surfaces[]")
            for item in _tuple_text(
                self.retained_external_surfaces,
                "retained_external_surfaces",
            )
        )
        if external != tuple(sorted(external)):
            raise ValueError("retained external surfaces must be sorted")
        if set(external) & set(paths):
            raise ValueError("retained external surfaces cannot also be release files")
        object.__setattr__(self, "retained_external_surfaces", external)
        phase_set = set(phase_ids)
        seen: set[str] = set()
        path_set = set(paths)
        for phase in self.phases:
            if any(dep not in seen for dep in phase.dependencies):
                raise ValueError(f"phase dependencies must precede {phase.phase_id}")
            if any(path not in path_set for path in phase.component_paths):
                raise ValueError(f"phase {phase.phase_id} references an untracked component")
            seen.add(phase.phase_id)
        for file in self.files:
            if any(phase not in phase_set for phase in file.phase_ids):
                raise ValueError(f"file {file.path} references an unknown phase")
        if type(self.generated_topology_authoritative) is not bool or self.generated_topology_authoritative:
            raise ValueError("generated topology must remain non-authoritative")
        if type(self.package_published) is not bool or self.package_published:
            raise ValueError("P9 cannot claim package publication")

    def payload_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "release_index_version": self.release_index_version,
            "verifier_version": self.verifier_version,
            "generated_topology_authoritative": False,
            "package_published": False,
            "retained_external_surfaces": list(self.retained_external_surfaces),
            "files": [item.to_dict() for item in self.files],
            "phases": [item.to_dict() for item in self.phases],
        }

    @property
    def digest(self) -> str:
        return hashlib.sha256(canonical_json(self.payload_dict()).encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {**self.payload_dict(), "manifest_digest": self.digest}


@dataclass(frozen=True)
class VerificationFinding:
    code: str
    message: str
    path: str | None = None
    blocking: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", _text(self.code, "finding.code"))
        object.__setattr__(self, "message", _text(self.message, "finding.message"))
        if self.path is not None:
            object.__setattr__(self, "path", _path(self.path, "finding.path"))
        if type(self.blocking) is not bool:
            raise ValueError("finding.blocking must be a boolean")

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "path": self.path,
            "blocking": self.blocking,
        }


@dataclass(frozen=True)
class VerificationReport:
    manifest_digest: str
    release_index_digest: str | None
    checked_files: int
    checked_symbols: int
    checked_versions: int
    findings: tuple[VerificationFinding, ...]
    version: str = SUBSTRATE_VERIFIER_VERSION

    def __post_init__(self) -> None:
        if self.version != SUBSTRATE_VERIFIER_VERSION:
            raise ValueError("unsupported verifier report version")
        if type(self.manifest_digest) is not str or not _HEX64.fullmatch(self.manifest_digest):
            raise ValueError("manifest_digest must be a lowercase SHA-256 digest")
        if self.release_index_digest is not None and (
            type(self.release_index_digest) is not str or not _HEX64.fullmatch(self.release_index_digest)
        ):
            raise ValueError("release_index_digest must be a lowercase SHA-256 digest")
        for name in ("checked_files", "checked_symbols", "checked_versions"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if type(self.findings) is not tuple or not all(isinstance(item, VerificationFinding) for item in self.findings):
            raise ValueError("findings must be a tuple of VerificationFinding")

    @property
    def passed(self) -> bool:
        return not any(item.blocking for item in self.findings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "manifest_digest": self.manifest_digest,
            "release_index_digest": self.release_index_digest,
            "checked_files": self.checked_files,
            "checked_symbols": self.checked_symbols,
            "checked_versions": self.checked_versions,
            "passed": self.passed,
            "findings": [item.to_dict() for item in self.findings],
        }


__all__ = [
    "CompatibilityMode",
    "ContractStatus",
    "FileRole",
    "MigrationStatus",
    "PATCH_AUTHORITY",
    "PhaseDisposition",
    "SUBSTRATE_MANIFEST_VERSION",
    "SUBSTRATE_RELEASE_INDEX_VERSION",
    "SUBSTRATE_VERIFIER_VERSION",
    "SubstrateFileRecord",
    "SubstrateManifest",
    "VerificationFinding",
    "VerificationReport",
]
