"""
Bob AI Integration Hooks for Automatic CODEMAP Refresh

This module provides integration points for Bob AI to automatically
refresh the CODEMAP after file modification operations.

Usage in Bob's tool handlers:
    from aura_bob_codemap_hooks import notify_file_modified

    # After write_to_file, apply_diff, or insert_content:
    notify_file_modified(file_path)
"""

from pathlib import Path

try:
    from aura_codemap_auto_refresh import flush_pending_refreshes, register_file_change
    _CODEMAP_AVAILABLE = True
    _register_file_change = register_file_change
    _flush_pending_refreshes = flush_pending_refreshes
except ImportError:
    _CODEMAP_AVAILABLE = False
    _register_file_change = None
    _flush_pending_refreshes = None


def notify_file_modified(file_path: str | Path) -> None:
    """Notify the CODEMAP system that a file has been modified.

    This should be called after any file write operation to keep
    the navigation index synchronized.

    Args:
        file_path: Path to the file that was modified
    """
    if not _CODEMAP_AVAILABLE or _register_file_change is None:
        return

    try:
        _register_file_change(file_path)
    except Exception:
        # Silently fail - don't break Bob's operations if CODEMAP fails
        pass


def notify_files_modified(file_paths: list[str | Path]) -> None:
    """Notify the CODEMAP system that multiple files have been modified.

    Args:
        file_paths: List of paths to files that were modified
    """
    if not _CODEMAP_AVAILABLE:
        return

    for path in file_paths:
        notify_file_modified(path)


def force_codemap_refresh() -> None:
    """Force an immediate CODEMAP refresh of all pending changes.

    This should be called before operations that depend on up-to-date
    navigation data, such as codebase searches or topology analysis.
    """
    if not _CODEMAP_AVAILABLE or _flush_pending_refreshes is None:
        return

    try:
        _flush_pending_refreshes()
    except Exception:
        # Silently fail
        pass


# Convenience decorator for Bob's tool functions
def auto_refresh_codemap(func):
    """Decorator to automatically refresh CODEMAP after a tool operation.

    Usage:
        @auto_refresh_codemap
        def write_to_file(path: str, content: str):
            # ... write file ...
            return path

    The decorator will extract the file path from the return value or
    from the 'path' parameter.
    """
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)

        # Try to extract file path from result or kwargs
        file_path: str | Path | None = None

        if isinstance(result, (str, Path)):
            file_path = result
        elif isinstance(result, dict) and 'path' in result:
            file_path = result['path']
        elif 'path' in kwargs:
            file_path = kwargs['path']
        elif len(args) > 0 and isinstance(args[0], (str, Path)):
            file_path = args[0]

        if file_path:
            notify_file_modified(file_path)

        return result

    return wrapper


# Example integration for Bob's existing tools
def integrate_with_bob_tools():
    """
    Example of how to integrate CODEMAP auto-refresh with Bob's tools.

    This would be called during Bob's initialization to wrap existing
    tool functions with automatic CODEMAP refresh.
    """
    # This is a template - actual integration would depend on Bob's architecture

    # Example: Wrap write_to_file
    # original_write_to_file = bob.tools.write_to_file
    # bob.tools.write_to_file = auto_refresh_codemap(original_write_to_file)

    # Example: Wrap apply_diff
    # original_apply_diff = bob.tools.apply_diff
    # bob.tools.apply_diff = auto_refresh_codemap(original_apply_diff)

    # Example: Wrap insert_content
    # original_insert_content = bob.tools.insert_content
    # bob.tools.insert_content = auto_refresh_codemap(original_insert_content)

    pass


if __name__ == "__main__":
    # Test the integration hooks
    print("Testing Bob CODEMAP integration hooks...")

    if _CODEMAP_AVAILABLE:
        print("✅ CODEMAP auto-refresh is available")

        # Test notification
        notify_file_modified("test_file.py")
        print("✅ File modification notification sent")

        # Test batch notification
        notify_files_modified(["file1.py", "file2.py", "file3.py"])
        print("✅ Batch file modification notifications sent")

        # Test force refresh
        force_codemap_refresh()
        print("✅ Force refresh completed")
    else:
        print("⚠️  CODEMAP auto-refresh not available (missing dependencies)")

    print("Test complete!")

# Made with Bob
