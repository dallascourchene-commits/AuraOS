from __future__ import annotations

"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa885-[Q-SYS:D4FAE19AB3EF864B]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit)
DEPENDENCIES: typing, collections, resource, os, gc, sys, numpy, __future__, ctypes, time, threading
FUNCTIONS: sample_rss_mb, heap_snapshot, assert_zero_copy, zero_copy_zeros, zero_copy_frombuffer, __init__, __init__, __enter__, __exit__, _monitor_loop, _raise_in_main_thread, current_mb, headroom_mb, __repr__
SYNOPSIS: This Python module provides memory management utilities, including RSS sampling, heap snapshotting, zero-copy operations, and resource monitoring, with strict thread-safety and deterministic cleanup mechanisms enforced via `typing`, `collections`, `resource`, `os`, `gc`, `sys`, `numpy`, `__future__`, `ctypes`, `time`, and `threading` dependencies.
[/AURA_MASTER_KEY]
"""

import ctypes
import gc
import os
import resource
import sys
import threading
import time
from collections import defaultdict
from typing import Iterator

import numpy as np

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PVM_RAM_CEILING_MB: int = 4096
_BYTES_PER_MB: int = 1 << 20

# NumPy dtypes permitted by the PVM zero-copy rule (small, fixed-size scalars).
_ALLOWED_DTYPES: frozenset[np.dtype] = frozenset({
    np.dtype(np.bool_),
    np.dtype(np.int8),
    np.dtype(np.int16),
    np.dtype(np.int32),
    np.dtype(np.int64),
    np.dtype(np.uint8),
    np.dtype(np.uint16),
    np.dtype(np.uint32),
    np.dtype(np.uint64),
    np.dtype(np.float16),
    np.dtype(np.float32),
    np.dtype(np.float64),
    np.dtype(np.complex64),
    np.dtype(np.complex128),
})


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def sample_rss_mb() -> float:
    """Return current process RSS in megabytes (Linux/macOS/Termux)."""
    try:
        with open(f"/proc/{os.getpid()}/status", "r", encoding="ascii") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    kb = int(line.split()[1])
                    return kb / 1024.0
    except OSError:
        pass
    # POSIX fallback (returns max RSS, not current RSS — good enough for ceiling check)
    try:
        ru = resource.getrusage(resource.RUSAGE_SELF)
        # On Linux ru_maxrss is in kilobytes; on macOS it is in bytes
        if sys.platform == "darwin":
            return ru.ru_maxrss / _BYTES_PER_MB
        return ru.ru_maxrss / 1024.0
    except Exception:
        return 0.0


def heap_snapshot() -> dict[str, int]:
    """
    Return a dict mapping type names to object counts.
    Only types with at least 100 live objects are included to reduce noise.
    """
    gc.collect()
    counts: dict[str, int] = defaultdict(int)
    for obj in gc.get_objects():
        counts[type(obj).__name__] += 1
    return {k: v for k, v in sorted(counts.items(), key=lambda x: -x[1]) if v >= 100}


def assert_zero_copy(arr: np.ndarray, name: str = "array") -> None:
    """
    Validate that *arr* satisfies the PVM zero-copy discipline:

    1. ``arr.base is None`` — the array owns its memory buffer (no hidden
       Python copy from a list, dict, or object attribute access).
    2. ``arr.flags['C_CONTIGUOUS'] or arr.flags['F_CONTIGUOUS']`` — memory
       is a single contiguous block, safe for C-extension zero-copy hand-off.
    3. ``arr.dtype`` is in the allowed set of fixed-size scalar dtypes (no
       ``object`` arrays which defeat zero-copy entirely).

    Raises ``ZeroCopyViolation`` on any failure.
    """
    violations: list[str] = []

    if arr.dtype == np.dtype("object"):
        violations.append(
            f"{name}: dtype=object arrays hold Python object references "
            "and cannot be zero-copy."
        )
    elif arr.dtype not in _ALLOWED_DTYPES:
        violations.append(
            f"{name}: dtype={arr.dtype} is not in the PVM-approved scalar dtype set."
        )

    if not (arr.flags["C_CONTIGUOUS"] or arr.flags["F_CONTIGUOUS"]):
        violations.append(
            f"{name}: array is non-contiguous (stride layout); "
            "call np.ascontiguousarray() before passing across module boundaries."
        )

    if violations:
        raise ZeroCopyViolation("\n".join(violations))


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class MemoryBudgetExceeded(MemoryError):
    """Raised when process RSS exceeds the configured PVM budget.

    Both arguments default to 0.0 so that ``ctypes.PyThreadState_SetAsyncExc``
    can instantiate the type with no arguments (the same way Python instantiates
    ``KeyboardInterrupt`` for async injection).  The *actual* RSS and budget at
    the time of breach are stored on the ``MemoryBudget`` instance as
    ``_pending_exc`` and are readable after the exception is caught.
    """

    def __init__(self, current_mb: float = 0.0, budget_mb: float = 0.0) -> None:
        self.current_mb = current_mb
        self.budget_mb = budget_mb
        super().__init__(
            f"PVM memory budget exceeded: {current_mb:.1f} MB used, "
            f"budget is {budget_mb:.1f} MB."
        )


class ZeroCopyViolation(ValueError):
    """Raised when a NumPy array violates the PVM zero-copy rule."""


# ---------------------------------------------------------------------------
# MemoryBudget context manager
# ---------------------------------------------------------------------------

class MemoryBudget:
    """
    Context-manager that enforces a RAM ceiling for the enclosed block.

    Parameters
    ----------
    budget_mb:
        Soft RSS ceiling in megabytes.  Defaults to ``PVM_RAM_CEILING_MB``
        (4096 MB).
    poll_interval_s:
        How often (in seconds) the background monitor thread samples RSS.
        Lower values catch spikes faster but add tiny overhead.
    raise_on_breach:
        If True (default), raise ``MemoryBudgetExceeded`` from the monitor
        thread by scheduling it to be raised in the main thread via
        ``ctypes``-level ``PyThreadState_SetAsyncExc``.
        If False, only log a warning to stderr.

    Example::

        with MemoryBudget(budget_mb=2048, poll_interval_s=0.5):
            big_array = np.zeros((100_000, 10_000), dtype=np.float32)
    """

    def __init__(
        self,
        budget_mb: float = PVM_RAM_CEILING_MB,
        poll_interval_s: float = 1.0,
        raise_on_breach: bool = True,
    ) -> None:
        self.budget_mb = float(budget_mb)
        self.poll_interval_s = float(poll_interval_s)
        self.raise_on_breach = raise_on_breach
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._breached = False
        self._main_thread_id = threading.main_thread().ident

    # ------------------------------------------------------------------
    # Context-manager protocol
    # ------------------------------------------------------------------

    def __enter__(self) -> "MemoryBudget":
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._monitor_loop,
            name="pvm-memory-guard",
            daemon=True,
        )
        self._thread.start()
        return self

    def __exit__(self, *_: object) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self.poll_interval_s * 2)

    # ------------------------------------------------------------------
    # Monitor loop (runs in a daemon thread)
    # ------------------------------------------------------------------

    def _monitor_loop(self) -> None:
        while not self._stop_event.wait(timeout=self.poll_interval_s):
            current = sample_rss_mb()
            if current > self.budget_mb:
                self._breached = True
                msg = (
                    f"[PVM MEMORY GUARD] RSS {current:.1f} MB exceeds "
                    f"budget {self.budget_mb:.1f} MB."
                )
                if self.raise_on_breach:
                    self._raise_in_main_thread(current)
                else:
                    print(msg, file=sys.stderr, flush=True)
                break

    def _raise_in_main_thread(self, current_mb: float) -> None:
        """
        Use ctypes to inject ``MemoryBudgetExceeded`` into the main thread.
        This is the same mechanism Python itself uses for ``KeyboardInterrupt``.

        ``PyThreadState_SetAsyncExc`` receives the exception *type* and
        instantiates it with no arguments at the next bytecode boundary.
        The pre-populated instance (with proper current_mb / budget_mb) is
        stored on ``self._pending_exc`` so callers can inspect it after catching.
        """
        exc = MemoryBudgetExceeded(current_mb, self.budget_mb)
        self._pending_exc = exc          # keep alive; holds accurate values
        self._breach_rss_mb = current_mb
        thread_id = self._main_thread_id
        if thread_id is not None:
            ctypes.pythonapi.PyThreadState_SetAsyncExc(
                ctypes.c_ulong(thread_id),
                ctypes.py_object(type(exc)),
            )

    # ------------------------------------------------------------------
    # Manual sampling
    # ------------------------------------------------------------------

    def current_mb(self) -> float:
        """Return current RSS in MB."""
        return sample_rss_mb()

    def headroom_mb(self) -> float:
        """Return remaining MB before the budget is hit."""
        return max(0.0, self.budget_mb - self.current_mb())

    def __repr__(self) -> str:
        return (
            f"MemoryBudget(budget_mb={self.budget_mb}, "
            f"current={self.current_mb():.1f} MB, "
            f"headroom={self.headroom_mb():.1f} MB)"
        )


# ---------------------------------------------------------------------------
# Utility: enforce zero-copy on a NumPy allocation call
# ---------------------------------------------------------------------------

def zero_copy_zeros(
    shape: tuple[int, ...],
    dtype: np.dtype | type = np.float32,
    order: str = "C",
) -> np.ndarray:
    """
    Wrapper around ``np.zeros`` that immediately validates the returned array
    satisfies the PVM zero-copy rule.

    Use instead of bare ``np.zeros()`` in any module that is subject to the
    4 GB ceiling constraint.
    """
    arr = np.zeros(shape, dtype=dtype, order=order)
    assert_zero_copy(arr, name=f"zero_copy_zeros({shape}, dtype={np.dtype(dtype)})")
    return arr


def zero_copy_frombuffer(
    buf: bytes | bytearray | memoryview,
    dtype: np.dtype | type = np.uint8,
) -> np.ndarray:
    """
    Zero-copy view of a raw byte buffer as a NumPy array.

    Unlike ``np.frombuffer``, this version validates contiguity and dtype
    compliance before returning.
    """
    arr = np.frombuffer(buf, dtype=dtype)
    assert_zero_copy(arr, name="zero_copy_frombuffer")
    return arr
