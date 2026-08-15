from __future__ import annotations

import io
import time
from contextlib import redirect_stderr

from pvm_memory_guard import MemoryBudget, MemoryBudgetExceeded, sample_rss_mb


def test_sync_memory_budget_enters_and_exits_without_poll_deadline_block() -> None:
    start = time.perf_counter()
    with MemoryBudget(
        budget_mb=sample_rss_mb() + 1024.0,
        poll_interval_s=0.05,
        raise_on_breach=False,
    ) as budget:
        assert budget.current_mb() > 0.0
    assert time.perf_counter() - start < 1.0


def test_sync_memory_budget_warn_monitor_runs_while_with_block_is_active() -> None:
    capture = io.StringIO()
    start = time.perf_counter()
    with redirect_stderr(capture):
        with MemoryBudget(
            budget_mb=max(0.01, sample_rss_mb() - 1.0),
            poll_interval_s=0.01,
            raise_on_breach=False,
        ):
            deadline = time.monotonic() + 0.5
            while "[PVM MEMORY GUARD]" not in capture.getvalue() and time.monotonic() < deadline:
                time.sleep(0.01)
    assert "[PVM MEMORY GUARD]" in capture.getvalue()
    assert time.perf_counter() - start < 1.0


def test_sync_memory_budget_raise_mode_interrupts_owner_thread() -> None:
    caught = False
    try:
        with MemoryBudget(
            budget_mb=max(0.01, sample_rss_mb() - 1.0),
            poll_interval_s=0.01,
            raise_on_breach=True,
        ):
            deadline = time.monotonic() + 1.0
            while time.monotonic() < deadline:
                time.sleep(0.02)
    except MemoryBudgetExceeded:
        caught = True
    assert caught is True
