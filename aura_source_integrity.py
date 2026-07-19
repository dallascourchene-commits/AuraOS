"""Strict UTF-8 source integrity checks for Aura repository text owners."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass
import hashlib
import os
from pathlib import Path
import stat
import subprocess
from typing import Any

SOURCE_INTEGRITY_VERSION = "AURA_SOURCE_INTEGRITY_V2"
SOURCE_DIGEST_ALGORITHM = "sha256-length-delimited-path-bytes-v1"
MAX_SOURCE_FILE_BYTES = 16 * 1024 * 1024
MAX_SOURCE_TREE_FILES = 10_000
MAX_SOURCE_TREE_BYTES = 512 * 1024 * 1024
_DEFAULT_SUFFIXES = frozenset({".py", ".pyi"})
_DEFAULT_EXCLUDED_PARTS = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "__pycache__",
        ".venv",
        "venv",
    }
)


@dataclass(frozen=True)
class SourceIntegrityFailure:
    path: str
    code: str
    message: str
    byte_offset: int
    offending_bytes_hex: str
    file_size: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SourceIntegrityError(ValueError):
    """Raised when a repository source file is not safe strict UTF-8 text."""

    def __init__(self, failure: SourceIntegrityFailure) -> None:
        super().__init__(failure.message)
        self.failure = failure


def _failure(
    path: Path,
    *,
    code: str,
    message: str,
    byte_offset: int,
    offending: bytes,
    file_size: int,
) -> SourceIntegrityError:
    return SourceIntegrityError(
        SourceIntegrityFailure(
            path=path.as_posix(),
            code=code,
            message=message,
            byte_offset=max(0, int(byte_offset)),
            offending_bytes_hex=offending.hex(),
            file_size=max(0, int(file_size)),
        )
    )


def _validate_limit(value: int, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _read_bounded_source_bytes(
    candidate: Path,
    *,
    maximum_bytes: int,
) -> tuple[bytes, int]:
    """Read at most ``maximum_bytes + 1`` bytes without following symlinks."""

    maximum_bytes = _validate_limit(maximum_bytes, name="maximum_bytes")
    try:
        before = candidate.lstat()
    except OSError as exc:
        raise _failure(
            candidate,
            code="SOURCE_FILESYSTEM_ERROR",
            message=f"unable to inspect source file: {candidate} ({exc})",
            byte_offset=0,
            offending=b"",
            file_size=0,
        ) from exc

    if stat.S_ISLNK(before.st_mode):
        raise _failure(
            candidate,
            code="SOURCE_SYMLINK_REJECTED",
            message=f"source symlinks are not allowed: {candidate}",
            byte_offset=0,
            offending=b"",
            file_size=before.st_size,
        )
    if not stat.S_ISREG(before.st_mode):
        raise _failure(
            candidate,
            code="SOURCE_NOT_REGULAR_FILE",
            message=f"source path is not a regular file: {candidate}",
            byte_offset=0,
            offending=b"",
            file_size=before.st_size,
        )
    if before.st_size > maximum_bytes:
        raise _failure(
            candidate,
            code="SOURCE_FILE_TOO_LARGE",
            message=f"source file exceeds {maximum_bytes} bytes: {candidate}",
            byte_offset=maximum_bytes,
            offending=b"",
            file_size=before.st_size,
        )

    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW

    descriptor: int | None = None
    try:
        descriptor = os.open(candidate, flags)
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise _failure(
                candidate,
                code="SOURCE_NOT_REGULAR_FILE",
                message=f"opened source is not a regular file: {candidate}",
                byte_offset=0,
                offending=b"",
                file_size=opened.st_size,
            )
        if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
            raise _failure(
                candidate,
                code="SOURCE_PATH_CHANGED",
                message=f"source path changed while being opened: {candidate}",
                byte_offset=0,
                offending=b"",
                file_size=opened.st_size,
            )
        if opened.st_size > maximum_bytes:
            raise _failure(
                candidate,
                code="SOURCE_FILE_TOO_LARGE",
                message=f"source file exceeds {maximum_bytes} bytes: {candidate}",
                byte_offset=maximum_bytes,
                offending=b"",
                file_size=opened.st_size,
            )
        with os.fdopen(descriptor, "rb", closefd=True) as handle:
            descriptor = None
            data = handle.read(maximum_bytes + 1)
            after = os.fstat(handle.fileno())
    except SourceIntegrityError:
        raise
    except OSError as exc:
        raise _failure(
            candidate,
            code="SOURCE_FILESYSTEM_ERROR",
            message=f"unable to read source file: {candidate} ({exc})",
            byte_offset=0,
            offending=b"",
            file_size=before.st_size,
        ) from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)

    file_size = max(before.st_size, opened.st_size, after.st_size, len(data))
    if len(data) > maximum_bytes or file_size > maximum_bytes:
        raise _failure(
            candidate,
            code="SOURCE_FILE_TOO_LARGE",
            message=f"source file exceeds {maximum_bytes} bytes: {candidate}",
            byte_offset=maximum_bytes,
            offending=b"",
            file_size=file_size,
        )
    return data, file_size


def _decode_source_bytes(candidate: Path, data: bytes, *, file_size: int) -> str:
    nul_at = data.find(b"\x00")
    if nul_at >= 0:
        raise _failure(
            candidate,
            code="SOURCE_NUL_BYTE",
            message=(
                f"source file contains a NUL byte at offset {nul_at}: "
                f"{candidate}"
            ),
            byte_offset=nul_at,
            offending=data[nul_at : nul_at + 1],
            file_size=file_size,
        )
    try:
        return data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        start = max(0, exc.start)
        stop = min(len(data), max(exc.end, start + 1))
        raise _failure(
            candidate,
            code="SOURCE_UTF8_INVALID",
            message=(
                f"source file is not strict UTF-8 at byte {start}: "
                f"{candidate} ({exc.reason})"
            ),
            byte_offset=start,
            offending=data[start:stop],
            file_size=file_size,
        ) from exc


def read_utf8_source(
    path: str | Path,
    *,
    maximum_bytes: int = MAX_SOURCE_FILE_BYTES,
) -> str:
    """Read one bounded regular source file as strict UTF-8."""

    candidate = Path(path)
    data, file_size = _read_bounded_source_bytes(
        candidate,
        maximum_bytes=maximum_bytes,
    )
    return _decode_source_bytes(candidate, data, file_size=file_size)


def _digest_record(hasher: Any, value: bytes) -> None:
    hasher.update(len(value).to_bytes(8, byteorder="big", signed=False))
    hasher.update(value)


def _source_digest(records: list[tuple[str, bytes]]) -> str:
    hasher = hashlib.sha256()
    _digest_record(hasher, SOURCE_INTEGRITY_VERSION.encode("ascii"))
    _digest_record(hasher, SOURCE_DIGEST_ALGORITHM.encode("ascii"))
    for normalized_path, data in records:
        _digest_record(hasher, normalized_path.encode("utf-8"))
        _digest_record(hasher, data)
    return hasher.hexdigest()


def _failure_dict(
    path: str,
    *,
    code: str,
    message: str,
    file_size: int = 0,
) -> dict[str, Any]:
    return SourceIntegrityFailure(
        path=path,
        code=code,
        message=message,
        byte_offset=0,
        offending_bytes_hex="",
        file_size=max(0, int(file_size)),
    ).to_dict()


def _git_source_binding(
    base: Path,
    *,
    expected_repository_head: str | None,
    require_git_tree: bool,
    candidate_paths: set[str],
    suffixes: frozenset[str],
    excluded_parts: frozenset[str],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    evidence: dict[str, Any] = {
        "repository_head": None,
        "repository_tree": None,
        "git_tree_bound": False,
        "git_binding_reason": "not_git_repository",
    }
    failures: list[dict[str, Any]] = []

    def git(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(base), *arguments],
            check=check,
            capture_output=True,
            text=True,
            timeout=20,
        )

    try:
        top_level = Path(git("rev-parse", "--show-toplevel").stdout.strip()).resolve()
        if top_level != base:
            evidence["git_binding_reason"] = "scan_root_is_not_repository_root"
            raise RuntimeError(evidence["git_binding_reason"])
        head = git("rev-parse", "HEAD").stdout.strip().lower()
        tree = git("rev-parse", "HEAD^{tree}").stdout.strip().lower()
        evidence["repository_head"] = head
        evidence["repository_tree"] = tree

        if expected_repository_head is not None:
            expected = str(expected_repository_head).strip().lower()
            if head != expected:
                failures.append(
                    _failure_dict(
                        ".",
                        code="SOURCE_HEAD_MISMATCH",
                        message=(
                            f"checked-out repository head {head} does not match "
                            f"expected head {expected}"
                        ),
                    )
                )

        unstaged = git("diff", "--quiet", "HEAD", "--", check=False).returncode
        staged = git("diff", "--cached", "--quiet", "HEAD", "--", check=False).returncode
        tracked_output = git("ls-files", "-z").stdout
        tracked_source_paths = {
            item
            for item in tracked_output.split("\0")
            if item
            and Path(item).suffix.lower() in suffixes
            and not (set(Path(item).parts) & excluded_parts)
        }
        source_set_matches = candidate_paths == tracked_source_paths
        if not source_set_matches:
            extra = sorted(candidate_paths - tracked_source_paths)[:20]
            missing = sorted(tracked_source_paths - candidate_paths)[:20]
            failures.append(
                _failure_dict(
                    ".",
                    code="SOURCE_GIT_SOURCE_SET_MISMATCH",
                    message=(
                        "working-tree source set differs from HEAD: "
                        f"extra={extra}, missing={missing}"
                    ),
                )
            )
        clean = unstaged == 0 and staged == 0 and source_set_matches
        head_matches = (
            expected_repository_head is None
            or head == str(expected_repository_head).strip().lower()
        )
        evidence["git_tree_bound"] = bool(clean and head_matches)
        if evidence["git_tree_bound"]:
            evidence["git_binding_reason"] = "clean_exact_head"
        elif not source_set_matches:
            evidence["git_binding_reason"] = "source_set_mismatch"
        else:
            evidence["git_binding_reason"] = "source_worktree_dirty"
        if require_git_tree and not evidence["git_tree_bound"]:
            failures.append(
                _failure_dict(
                    ".",
                    code="SOURCE_GIT_TREE_UNBOUND",
                    message="source evidence is not bound to a clean exact Git tree",
                )
            )
    except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
        if require_git_tree or expected_repository_head is not None:
            failures.append(
                _failure_dict(
                    ".",
                    code="SOURCE_GIT_EVIDENCE_UNAVAILABLE",
                    message=f"unable to establish exact Git source evidence: {exc}",
                )
            )
    return evidence, failures


def scan_utf8_source_tree(
    root: str | Path,
    *,
    suffixes: Iterable[str] = _DEFAULT_SUFFIXES,
    excluded_parts: Iterable[str] = _DEFAULT_EXCLUDED_PARTS,
    maximum_files: int = MAX_SOURCE_TREE_FILES,
    maximum_total_bytes: int = MAX_SOURCE_TREE_BYTES,
    expected_repository_head: str | None = None,
    require_git_tree: bool = False,
) -> dict[str, Any]:
    """Scan source deterministically without mutation and emit bounded evidence."""

    maximum_files = _validate_limit(maximum_files, name="maximum_files")
    maximum_total_bytes = _validate_limit(
        maximum_total_bytes,
        name="maximum_total_bytes",
    )
    base = Path(root).resolve(strict=True)
    suffix_set = frozenset(str(item).lower() for item in suffixes)
    excluded = frozenset(str(item) for item in excluded_parts)
    failures: list[dict[str, Any]] = []
    records: list[tuple[str, bytes]] = []
    checked_bytes = 0
    checked_file_count = 0
    candidate_file_count = 0
    candidate_paths: set[str] = set()
    limit_reached = False

    def walk_error(exc: OSError) -> None:
        filename = Path(exc.filename) if exc.filename else base
        try:
            relative = filename.relative_to(base).as_posix()
        except ValueError:
            relative = filename.as_posix()
        failures.append(
            _failure_dict(
                relative,
                code="SOURCE_FILESYSTEM_ERROR",
                message=f"unable to enumerate source path: {filename} ({exc})",
            )
        )

    for current, directory_names, file_names in os.walk(
        base,
        topdown=True,
        followlinks=False,
        onerror=walk_error,
    ):
        current_path = Path(current)
        kept_directories: list[str] = []
        for name in sorted(directory_names):
            directory = current_path / name
            relative = directory.relative_to(base)
            if set(relative.parts) & excluded:
                continue
            try:
                metadata = directory.lstat()
            except OSError as exc:
                failures.append(
                    _failure_dict(
                        relative.as_posix(),
                        code="SOURCE_FILESYSTEM_ERROR",
                        message=f"unable to inspect source directory: {directory} ({exc})",
                    )
                )
                continue
            if stat.S_ISLNK(metadata.st_mode):
                failures.append(
                    _failure_dict(
                        relative.as_posix(),
                        code="SOURCE_SYMLINK_REJECTED",
                        message=f"source-tree symlink directory rejected: {relative}",
                        file_size=metadata.st_size,
                    )
                )
                continue
            kept_directories.append(name)
        directory_names[:] = kept_directories

        for name in sorted(file_names):
            candidate = current_path / name
            relative = candidate.relative_to(base)
            if candidate.suffix.lower() not in suffix_set:
                continue
            if set(relative.parts) & excluded:
                continue
            candidate_file_count += 1
            normalized_path = relative.as_posix()
            candidate_paths.add(normalized_path)
            if candidate_file_count > maximum_files:
                failures.append(
                    _failure_dict(
                        normalized_path,
                        code="SOURCE_FILE_COUNT_LIMIT",
                        message=f"source candidate count exceeds {maximum_files}",
                    )
                )
                limit_reached = True
                break
            try:
                metadata = candidate.lstat()
                if stat.S_ISLNK(metadata.st_mode):
                    raise _failure(
                        candidate,
                        code="SOURCE_SYMLINK_REJECTED",
                        message=f"source symlinks are not allowed: {candidate}",
                        byte_offset=0,
                        offending=b"",
                        file_size=metadata.st_size,
                    )
                resolved = candidate.resolve(strict=True)
                try:
                    resolved.relative_to(base)
                except ValueError as exc:
                    raise _failure(
                        candidate,
                        code="SOURCE_OUTSIDE_ROOT",
                        message=f"source resolves outside repository root: {candidate}",
                        byte_offset=0,
                        offending=b"",
                        file_size=metadata.st_size,
                    ) from exc
                if checked_bytes + metadata.st_size > maximum_total_bytes:
                    failures.append(
                        _failure_dict(
                            normalized_path,
                            code="SOURCE_TREE_BYTES_LIMIT",
                            message=(
                                "source tree exceeds aggregate byte ceiling "
                                f"{maximum_total_bytes}"
                            ),
                            file_size=metadata.st_size,
                        )
                    )
                    limit_reached = True
                    break
                data, file_size = _read_bounded_source_bytes(
                    candidate,
                    maximum_bytes=MAX_SOURCE_FILE_BYTES,
                )
                if checked_bytes + len(data) > maximum_total_bytes:
                    failures.append(
                        _failure_dict(
                            normalized_path,
                            code="SOURCE_TREE_BYTES_LIMIT",
                            message=(
                                "source tree exceeds aggregate byte ceiling "
                                f"{maximum_total_bytes}"
                            ),
                            file_size=file_size,
                        )
                    )
                    limit_reached = True
                    break
                records.append((normalized_path, data))
                checked_file_count += 1
                checked_bytes += len(data)
                _decode_source_bytes(candidate, data, file_size=file_size)
            except SourceIntegrityError as exc:
                failure = exc.failure.to_dict()
                failure["path"] = normalized_path
                failures.append(failure)
            except OSError as exc:
                failures.append(
                    _failure_dict(
                        normalized_path,
                        code="SOURCE_FILESYSTEM_ERROR",
                        message=f"unable to process source file: {candidate} ({exc})",
                    )
                )
        if limit_reached:
            break

    git_evidence, git_failures = _git_source_binding(
        base,
        expected_repository_head=expected_repository_head,
        require_git_tree=require_git_tree,
        candidate_paths=candidate_paths,
        suffixes=suffix_set,
        excluded_parts=excluded,
    )
    failures.extend(git_failures)
    failures.sort(key=lambda item: (str(item["path"]), str(item["code"])))
    digest = _source_digest(records)
    return {
        "version": SOURCE_INTEGRITY_VERSION,
        "status": "PASSED" if not failures else "FAILED",
        "evidence_scope": (
            "git_tree_bound" if git_evidence["git_tree_bound"] else "working_tree_only"
        ),
        "source_digest_algorithm": SOURCE_DIGEST_ALGORITHM,
        "source_digest": digest,
        "candidate_file_count": candidate_file_count,
        "checked_file_count": checked_file_count,
        "checked_bytes": checked_bytes,
        "maximum_files": maximum_files,
        "maximum_total_bytes": maximum_total_bytes,
        "limit_reached": limit_reached,
        "failure_count": len(failures),
        "failures": failures,
        **git_evidence,
        "production_mutation": False,
        "automatic_fix": False,
        "human_review_required": True,
    }


__all__ = [
    "MAX_SOURCE_FILE_BYTES",
    "MAX_SOURCE_TREE_BYTES",
    "MAX_SOURCE_TREE_FILES",
    "SOURCE_DIGEST_ALGORITHM",
    "SOURCE_INTEGRITY_VERSION",
    "SourceIntegrityError",
    "SourceIntegrityFailure",
    "read_utf8_source",
    "scan_utf8_source_tree",
]
