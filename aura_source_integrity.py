"""Strict UTF-8 source integrity checks for Aura repository text owners."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

SOURCE_INTEGRITY_VERSION = "AURA_SOURCE_INTEGRITY_V1"
MAX_SOURCE_FILE_BYTES = 16 * 1024 * 1024
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


def read_utf8_source(
    path: str | Path,
    *,
    maximum_bytes: int = MAX_SOURCE_FILE_BYTES,
) -> str:
    """Read one bounded source file as strict UTF-8 and reject NUL/corruption."""

    candidate = Path(path)
    data = candidate.read_bytes()
    if len(data) > maximum_bytes:
        raise _failure(
            candidate,
            code="SOURCE_FILE_TOO_LARGE",
            message=f"source file exceeds {maximum_bytes} bytes: {candidate}",
            byte_offset=maximum_bytes,
            offending=b"",
            file_size=len(data),
        )
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
            file_size=len(data),
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
            file_size=len(data),
        ) from exc


def scan_utf8_source_tree(
    root: str | Path,
    *,
    suffixes: Iterable[str] = _DEFAULT_SUFFIXES,
    excluded_parts: Iterable[str] = _DEFAULT_EXCLUDED_PARTS,
) -> dict[str, Any]:
    """Scan repository source files deterministically without mutating them."""

    base = Path(root).resolve()
    suffix_set = frozenset(str(item).lower() for item in suffixes)
    excluded = frozenset(str(item) for item in excluded_parts)
    paths = sorted(
        path
        for path in base.rglob("*")
        if path.is_file()
        and path.suffix.lower() in suffix_set
        and not (set(path.relative_to(base).parts) & excluded)
    )
    failures: list[dict[str, Any]] = []
    checked_bytes = 0
    for path in paths:
        checked_bytes += path.stat().st_size
        try:
            read_utf8_source(path)
        except SourceIntegrityError as exc:
            failure = exc.failure.to_dict()
            failure["path"] = path.relative_to(base).as_posix()
            failures.append(failure)
    return {
        "version": SOURCE_INTEGRITY_VERSION,
        "status": "PASSED" if not failures else "FAILED",
        "checked_file_count": len(paths),
        "checked_bytes": checked_bytes,
        "failure_count": len(failures),
        "failures": failures,
        "production_mutation": False,
        "automatic_fix": False,
        "human_review_required": True,
    }


__all__ = [
    "MAX_SOURCE_FILE_BYTES",
    "SOURCE_INTEGRITY_VERSION",
    "SourceIntegrityError",
    "SourceIntegrityFailure",
    "read_utf8_source",
    "scan_utf8_source_tree",
]
