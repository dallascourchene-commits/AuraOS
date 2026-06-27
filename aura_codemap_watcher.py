#!/usr/bin/env python3
"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8c7-[Q-SYS:CODEMAP_FILE_WATCHER]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Integrity / Universal File Monitoring)
DEPENDENCIES: pathlib, time, threading, watchdog
FUNCTIONS: start_watcher, stop_watcher, CodeMapFileWatcher
SYNOPSIS: Universal file system watcher that monitors workspace for code changes from ANY source (Bob, VS Code, Cline, manual edits) and automatically triggers CODEMAP refresh.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from pathlib import Path
import sys
import threading
import time

try:
    from watchdog.events import FileSystemEvent, FileSystemEventHandler
    from watchdog.observers import Observer
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None
    FileSystemEventHandler = None
    FileSystemEvent = None

from aura_bob_codemap_hooks import notify_file_modified

# File extensions to monitor
CODE_EXTENSIONS = {'.py', '.rs', '.c', '.cpp', '.h', '.hpp', '.js', '.ts', '.java', '.go', '.rb', '.php'}

# Directories to ignore
IGNORE_DIRS = {
    '.git', '__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache',
    'node_modules', '.venv', 'venv', 'env', '.aura', 'Aura_Memory',
    '.vscode', '.idea', 'build', 'dist', 'target'
}

# Global watcher instance
_watcher_instance: CodeMapWatcher | None = None
_watcher_lock = threading.Lock()


class CodeMapFileHandler(FileSystemEventHandler):
    """File system event handler that triggers CODEMAP refresh on code changes."""

    def __init__(self, debounce_seconds: float = 0.5):
        super().__init__()
        self.debounce_seconds = debounce_seconds
        self.pending_files: set[Path] = set()
        self.last_event_time: dict[Path, float] = {}
        self.lock = threading.Lock()

    def should_process(self, path: Path) -> bool:
        """Check if file should trigger CODEMAP refresh."""
        # Check extension
        if path.suffix not in CODE_EXTENSIONS:
            return False

        # Check if in ignored directory
        for part in path.parts:
            if part in IGNORE_DIRS:
                return False

        # Check if it's a temporary file
        if path.name.startswith('.') or path.name.endswith('~'):
            return False

        return True

    def debounce_event(self, path: Path) -> bool:
        """Debounce rapid file events (e.g., save operations)."""
        now = time.time()
        with self.lock:
            last_time = self.last_event_time.get(path, 0)
            if now - last_time < self.debounce_seconds:
                return False  # Too soon, skip this event
            self.last_event_time[path] = now
            return True

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events."""
        if event.is_directory:
            return

        path = Path(event.src_path)

        if not self.should_process(path):
            return

        if not self.debounce_event(path):
            return

        # Notify CODEMAP system
        notify_file_modified(path)
        print(f"[CODEMAP Watcher] Change detected: {path.name}")

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events."""
        if event.is_directory:
            return

        path = Path(event.src_path)

        if not self.should_process(path):
            return

        # Notify CODEMAP system
        notify_file_modified(path)
        print(f"[CODEMAP Watcher] New file: {path.name}")

    def on_moved(self, event: FileSystemEvent) -> None:
        """Handle file move/rename events."""
        if event.is_directory:
            return

        # Notify for both old and new paths
        if hasattr(event, 'dest_path'):
            dest_path = Path(event.dest_path)
            if self.should_process(dest_path):
                notify_file_modified(dest_path)
                print(f"[CODEMAP Watcher] Renamed: {dest_path.name}")


class CodeMapWatcher:
    """Universal file system watcher for automatic CODEMAP refresh."""

    def __init__(self, workspace_path: str | Path = ".", debounce_seconds: float = 0.5):
        if not WATCHDOG_AVAILABLE:
            raise ImportError(
                "watchdog library not available. Install with: pip install watchdog"
            )

        self.workspace_path = Path(workspace_path).resolve()
        self.debounce_seconds = debounce_seconds
        self.observer: Observer | None = None
        self.handler: CodeMapFileHandler | None = None
        self.is_running = False

    def start(self) -> None:
        """Start watching the workspace for file changes."""
        if self.is_running:
            print("[CODEMAP Watcher] Already running")
            return

        if not self.workspace_path.exists():
            raise ValueError(f"Workspace path does not exist: {self.workspace_path}")

        print("[CODEMAP Watcher] Starting file system monitor...")
        print(f"[CODEMAP Watcher] Watching: {self.workspace_path}")
        print(f"[CODEMAP Watcher] Monitoring extensions: {', '.join(sorted(CODE_EXTENSIONS))}")

        self.handler = CodeMapFileHandler(debounce_seconds=self.debounce_seconds)
        self.observer = Observer()
        self.observer.schedule(self.handler, str(self.workspace_path), recursive=True)
        self.observer.start()
        self.is_running = True

        print("[CODEMAP Watcher] [OK] File system monitor active")
        print("[CODEMAP Watcher] CODEMAP will auto-refresh on code changes from ANY source")

    def stop(self) -> None:
        """Stop watching the workspace."""
        if not self.is_running:
            return

        print("[CODEMAP Watcher] Stopping file system monitor...")

        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=5.0)

        self.is_running = False
        print("[CODEMAP Watcher] [OK] File system monitor stopped")

    def run_forever(self) -> None:
        """Run the watcher indefinitely (blocking)."""
        self.start()
        try:
            while self.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[CODEMAP Watcher] Received interrupt signal")
        finally:
            self.stop()


def start_watcher(workspace_path: str | Path = ".", debounce_seconds: float = 0.5) -> CodeMapWatcher:
    """Start the global CODEMAP file system watcher.

    Args:
        workspace_path: Path to workspace directory to monitor
        debounce_seconds: Minimum time between events for same file

    Returns:
        CodeMapWatcher instance

    Raises:
        ImportError: If watchdog library is not installed
        ValueError: If workspace path doesn't exist
    """
    global _watcher_instance

    with _watcher_lock:
        if _watcher_instance is not None and _watcher_instance.is_running:
            print("[CODEMAP Watcher] Watcher already running")
            return _watcher_instance

        _watcher_instance = CodeMapWatcher(workspace_path, debounce_seconds)
        _watcher_instance.start()
        return _watcher_instance


def stop_watcher() -> None:
    """Stop the global CODEMAP file system watcher."""
    global _watcher_instance

    with _watcher_lock:
        if _watcher_instance is not None:
            _watcher_instance.stop()
            _watcher_instance = None


def get_watcher() -> CodeMapWatcher | None:
    """Get the current watcher instance, if any."""
    return _watcher_instance


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="CODEMAP File System Watcher - Monitors workspace for code changes"
    )
    parser.add_argument(
        "--workspace",
        default=".",
        help="Workspace directory to monitor (default: current directory)"
    )
    parser.add_argument(
        "--debounce",
        type=float,
        default=0.5,
        help="Debounce interval in seconds (default: 0.5)"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run in test mode (exits after 10 seconds)"
    )

    args = parser.parse_args()

    if not WATCHDOG_AVAILABLE:
        print("ERROR: watchdog library not installed")
        print("Install with: pip install watchdog")
        sys.exit(1)

    print("=" * 70)
    print("CODEMAP Universal File System Watcher")
    print("=" * 70)
    print()
    print("This watcher monitors your workspace for code changes from ANY source:")
    print("  • Bob AI file modifications")
    print("  • VS Code edits")
    print("  • Cline edits")
    print("  • Manual file edits")
    print("  • Git operations")
    print("  • Any other tool")
    print()
    print("When code files are modified, CODEMAP will automatically refresh")
    print("to keep navigation data accurate.")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 70)
    print()

    try:
        watcher = start_watcher(args.workspace, args.debounce)

        if args.test:
            print("\n[Test Mode] Running for 10 seconds...")
            time.sleep(10)
            print("[Test Mode] Test complete, stopping...")
        else:
            watcher.run_forever()

    except ImportError as e:
        print(f"\nERROR: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"\nERROR: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nShutting down gracefully...")
    finally:
        stop_watcher()
        print("\n[OK] CODEMAP watcher stopped")

# Made with Bob
