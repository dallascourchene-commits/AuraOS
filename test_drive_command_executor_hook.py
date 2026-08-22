"""Root-level pytest discovery shim for the Project006 Drive executor hook tests."""

from tools.project006.test_drive_command_executor_hook import (
    DriveCommandExecutorHookTests as TestDriveCommandExecutorHook,
)

__all__ = ["TestDriveCommandExecutorHook"]
