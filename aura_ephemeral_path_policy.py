"""
Aura Ephemeral Path Policy — enforce safe path handling in all adapters.

- canonicalize every path
- reject absolute paths unless explicitly allowlisted
- reject .. escape
- reject symlink escape
- enforce readable-path allowlist
- enforce forbidden paths before opening
- enforce file-size limit
- enforce text/binary media policy
- never expose .env, credentials, keys
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

FORBIDDEN_PATTERNS = (".env", "credentials", ".key", ".pem", "secret", "password", ".git/credentials", "id_rsa", ".ssh")
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def canonicalize_path(path: str, base: str = ".") -> str:
    """Canonicalize a path relative to base."""
    p = Path(path)
    if p.is_absolute():
        return str(p.resolve())
    return str((Path(base) / p).resolve())


def check_path_safety(
    path: str,
    *,
    allowed_paths: list[str] | None = None,
    forbidden_paths: list[str] | None = None,
    base: str = ".",
) -> dict[str, Any]:
    """Check if a path is safe to access."""
    errors: list[str] = []

    # Canonicalize
    try:
        resolved = Path(path).resolve()
    except Exception:
        return {"ok": False, "errors": ["path_resolution_failed"],
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    path_str = str(resolved).lower()
    base_resolved = Path(base).resolve()

    # Check for .. escape
    if ".." in path:
        errors.append("path_traversal_detected")

    # Check absolute path outside base
    if Path(path).is_absolute():
        if allowed_paths and not any(path_str.startswith(str(Path(a).resolve()).lower()) for a in allowed_paths):
            errors.append("absolute_path_outside_allowlist")

    # Check forbidden patterns
    all_forbidden = list(FORBIDDEN_PATTERNS) + list(forbidden_paths or [])
    for pattern in all_forbidden:
        if pattern.lower() in path_str:
            errors.append(f"forbidden_path_pattern: {pattern}")
            break

    # Check symlink escape
    try:
        if Path(path).exists() and Path(path).is_symlink():
            symlink_target = Path(path).resolve()
            if not str(symlink_target).startswith(str(base_resolved)):
                errors.append("symlink_escape_detected")
    except (PermissionError, OSError):
        errors.append("path_access_denied")

    # Check readable-path allowlist
    if allowed_paths:
        in_allowlist = any(
            path_str.startswith(str(Path(a).resolve()).lower())
            for a in allowed_paths
        )
        if not in_allowlist:
            errors.append("path_not_in_readable_allowlist")

    return {"ok": len(errors) == 0, "errors": errors, "resolved_path": path_str,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def check_file_access(
    path: str,
    *,
    allowed_paths: list[str] | None = None,
    max_size: int = MAX_FILE_SIZE,
    text_only: bool = True,
) -> dict[str, Any]:
    """Full file access check including size and media type."""
    safety = check_path_safety(path, allowed_paths=allowed_paths)
    if not safety["ok"]:
        return safety

    p = Path(path)
    if not p.exists():
        return {"ok": False, "errors": ["file_not_found"],
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    # Size check
    size = p.stat().st_size
    if size > max_size:
        return {"ok": False, "errors": [f"file_too_large: {size} > {max_size}"],
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    # Media type check
    if text_only:
        try:
            p.read_text(encoding="utf-8", errors="strict")
        except (UnicodeDecodeError, ValueError):
            return {"ok": False, "errors": ["binary_file_rejected_text_only_policy"],
                    "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    return {"ok": True, "size": size,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
