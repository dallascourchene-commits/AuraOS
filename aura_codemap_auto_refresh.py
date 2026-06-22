"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8c6-[Q-SYS:CODEMAP_AUTO_REFRESH]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Integrity / Auto-maintained Navigation)
DEPENDENCIES: pathlib, threading, time, aura_codebase_navigator
FUNCTIONS: auto_refresh_codemap, register_file_change, flush_pending_refreshes
SYNOPSIS: Automatic CODEMAP refresh system that tracks file modifications and batches updates to keep navigation index current without manual intervention.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

import atexit
from pathlib import Path
import threading
import time
from typing import Set

from aura_codebase_navigator import (
    DEFAULT_INDEX_PATH,
    DEFAULT_TOPOLOGY_PATH,
    refresh_index_for_paths,
    write_navigation_artifacts,
)

# Global state for tracking pending refreshes
_pending_changes: Set[Path] = set()
_refresh_lock = threading.Lock()
_last_refresh_time = 0.0
_refresh_interval = 2.0  # Batch changes within 2 seconds
_auto_refresh_enabled = True
_refresh_timer: threading.Timer | None = None


def enable_auto_refresh(enabled: bool = True) -> None:
    """Enable or disable automatic CODEMAP refresh."""
    global _auto_refresh_enabled
    _auto_refresh_enabled = enabled


def set_refresh_interval(seconds: float) -> None:
    """Set the batching interval for refresh operations (default: 2.0 seconds)."""
    global _refresh_interval
    _refresh_interval = max(0.5, seconds)


def register_file_change(file_path: str | Path) -> None:
    """Register a file change for batched CODEMAP refresh.
    
    This should be called after any file write operation (write_to_file, 
    apply_diff, insert_content) to keep the CODEMAP synchronized.
    
    Args:
        file_path: Path to the file that was modified
    """
    if not _auto_refresh_enabled:
        return
    
    path = Path(file_path)
    
    # Skip non-code files and generated artifacts
    if path.suffix not in {".py", ".rs", ".c", ".cpp", ".js", ".ts", ".java", ".go"}:
        return
    
    if ".aura" in path.parts or "__pycache__" in path.parts:
        return
    
    with _refresh_lock:
        _pending_changes.add(path)
        _schedule_refresh()


def _schedule_refresh() -> None:
    """Schedule a batched refresh after the configured interval."""
    global _refresh_timer
    
    # Cancel existing timer if present
    if _refresh_timer is not None:
        _refresh_timer.cancel()
    
    # Schedule new refresh
    _refresh_timer = threading.Timer(_refresh_interval, _execute_refresh)
    _refresh_timer.daemon = True
    _refresh_timer.start()


def _execute_refresh() -> None:
    """Execute the batched CODEMAP refresh for all pending changes."""
    global _last_refresh_time, _refresh_timer
    
    with _refresh_lock:
        if not _pending_changes:
            _refresh_timer = None
            return
        
        # Copy and clear pending changes
        changes_to_process = list(_pending_changes)
        _pending_changes.clear()
        _refresh_timer = None
    
    try:
        # Perform the refresh
        index_path = Path(DEFAULT_INDEX_PATH)
        
        if not index_path.exists():
            # CODEMAP doesn't exist yet, skip auto-refresh
            return
        
        # Refresh the index for changed files
        updated_payload = refresh_index_for_paths(
            index_path=index_path,
            changed_paths=changes_to_process,
            include_topology=True,
            topology_path=Path(DEFAULT_TOPOLOGY_PATH),
            refresh_topology=False,  # Don't rebuild full topology on every change
        )
        
        # Write updated artifacts
        write_navigation_artifacts(
            payload=updated_payload,
            json_path=index_path,
            md_path=Path(".aura/CODEMAP.md"),
        )
        
        _last_refresh_time = time.time()
        
        # Log the refresh (optional, can be disabled for silent operation)
        file_list = ", ".join(p.name for p in changes_to_process[:3])
        if len(changes_to_process) > 3:
            file_list += f" (+{len(changes_to_process) - 3} more)"
        print(f"[CODEMAP] Auto-refreshed: {file_list}")
        
    except Exception as e:
        # Don't crash on refresh errors, just log
        print(f"[CODEMAP] Auto-refresh failed: {e}")


def flush_pending_refreshes() -> None:
    """Immediately flush all pending CODEMAP refreshes.
    
    This should be called before critical operations that depend on 
    up-to-date navigation data, or before program exit.
    """
    global _refresh_timer
    
    # Cancel scheduled timer
    if _refresh_timer is not None:
        _refresh_timer.cancel()
        _refresh_timer = None
    
    # Execute refresh immediately if there are pending changes
    if _pending_changes:
        _execute_refresh()


def get_pending_changes() -> list[Path]:
    """Get list of files with pending CODEMAP updates."""
    with _refresh_lock:
        return list(_pending_changes)


# Register cleanup on exit
atexit.register(flush_pending_refreshes)


# Convenience function for direct use
def auto_refresh_codemap(file_path: str | Path) -> None:
    """Convenience function: register file change and optionally flush immediately.
    
    Args:
        file_path: Path to the file that was modified
    """
    register_file_change(file_path)


if __name__ == "__main__":
    # Test the auto-refresh system
    print("Testing CODEMAP auto-refresh system...")
    
    # Simulate some file changes
    test_files = ["aura_node.py", "aura_core.py", "aura_substrate.py"]
    
    for file in test_files:
        register_file_change(file)
        print(f"Registered: {file}")
    
    print(f"Pending changes: {len(get_pending_changes())}")
    print("Waiting for batched refresh...")
    
    # Wait for refresh to complete
    time.sleep(_refresh_interval + 1)
    
    print(f"Pending changes after refresh: {len(get_pending_changes())}")
    print("Test complete!")

# Made with Bob
