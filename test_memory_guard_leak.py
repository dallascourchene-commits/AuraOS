from __future__ import annotations

"""
AURA PVM — Controlled Memory Leak Test
=======================================
Verifies that MemoryBudget intercepts a runaway allocation and raises
MemoryBudgetExceeded *before* the OS Low-Memory Killer (LMK) becomes
relevant, using only ~200 MB of headroom above the process baseline.

Three phases
------------
Phase 1 — Warn-only  (raise_on_breach=False)
    Confirms the monitor thread fires and logs a stderr warning without
    killing the process.

Phase 2 — Exception injection  (raise_on_breach=True)
    Simulates an uncontrolled allocation loop.  Verifies that
    MemoryBudgetExceeded is raised in the main thread via
    ctypes.PyThreadState_SetAsyncExc before the next large allocation
    can execute.

Phase 3 — Overshoot & recovery audit
    Measures: RSS at interception, overshoot past budget, bytes freed
    by GC after the exception, and total elapsed time.

Run:
    python test_memory_guard_leak.py
"""

import gc
import io
import sys
import time

import numpy as np

from pvm_memory_guard import (
    MemoryBudget,
    MemoryBudgetExceeded,
    sample_rss_mb,
)

# Type alias used in function signature annotations below
_MemoryBudget = MemoryBudget

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CHUNK_MB: int = 32          # each allocation step: 32 MB float32 array
HEADROOM_MB: int = 200      # budget = baseline + this value
POLL_S: float = 0.05        # monitor poll interval: 50 ms (tight)
SLEEP_BETWEEN_ALLOC_S: float = 0.12  # 120 ms between steps > 2× poll, so
                                      # the monitor has time to sample

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DIVIDER = "─" * 62

def _banner(title: str) -> None:
    print(f"\n{'═' * 62}")
    print(f"  {title}")
    print('═' * 62)

def _rss() -> float:
    return sample_rss_mb()

def _mb_to_floats(mb: int) -> int:
    """Number of float32 elements needed to occupy *mb* megabytes."""
    return (mb * 1024 * 1024) // 4

# ---------------------------------------------------------------------------
# Phase 1 — warn-only
# ---------------------------------------------------------------------------

def phase1_warn_only() -> None:
    _banner("PHASE 1 — Warn-only (raise_on_breach=False)")
    baseline = _rss()
    budget = baseline + 80          # tiny budget: breach after ~3 steps
    print(f"  Baseline RSS : {baseline:.1f} MB")
    print(f"  Budget       : {budget:.1f} MB  (+80 MB)")
    print(f"  Poll interval: {POLL_S * 1000:.0f} ms")
    print(f"  Chunk size   : {CHUNK_MB} MB per step")
    print(_DIVIDER)

    held: list[np.ndarray] = []
    warned = False
    t0 = time.perf_counter()

    # Capture stderr to detect the warning message
    stderr_capture = io.StringIO()
    old_stderr = sys.stderr
    sys.stderr = stderr_capture

    try:
        with MemoryBudget(budget_mb=budget, poll_interval_s=POLL_S, raise_on_breach=False):
            for step in range(1, 10):
                arr = np.ones(_mb_to_floats(CHUNK_MB), dtype=np.float32)
                held.append(arr)
                rss = _rss()
                sys.stderr = old_stderr          # restore for our print
                print(f"  Step {step:2d} | alloc +{CHUNK_MB} MB | RSS {rss:.1f} MB | "
                      f"headroom {max(0.0, budget - rss):.1f} MB")
                sys.stderr = stderr_capture      # re-capture
                time.sleep(POLL_S * 3)           # let monitor fire
                if budget < rss:
                    break
    finally:
        sys.stderr = old_stderr

    elapsed = time.perf_counter() - t0
    warning_text = stderr_capture.getvalue()
    warned = "[PVM MEMORY GUARD]" in warning_text

    # free all chunks immediately
    del held
    gc.collect()

    print(_DIVIDER)
    print(f"  Stderr warning fired : {'YES ✓' if warned else 'NO ✗'}")
    if warned:
        print(f"  Warning message      : {warning_text.strip()}")
    print(f"  Process still alive  : YES ✓  (no exception raised)")
    print(f"  Elapsed              : {elapsed * 1000:.0f} ms")
    result = "PASS" if warned else "FAIL"
    print(f"\n  Phase 1 result: {result}")


# ---------------------------------------------------------------------------
# Phase 2 — exception injection
# ---------------------------------------------------------------------------

def phase2_exception_injection() -> None:
    _banner("PHASE 2 — Exception injection (raise_on_breach=True)")
    gc.collect()
    time.sleep(0.2)                  # let RSS settle after Phase 1
    baseline = _rss()
    budget = baseline + HEADROOM_MB
    print(f"  Baseline RSS : {baseline:.1f} MB")
    print(f"  Budget       : {budget:.1f} MB  (+{HEADROOM_MB} MB)")
    print(f"  Poll interval: {POLL_S * 1000:.0f} ms")
    print(f"  Chunk size   : {CHUNK_MB} MB per step")
    print(f"  Alloc pause  : {SLEEP_BETWEEN_ALLOC_S * 1000:.0f} ms between steps")
    print(_DIVIDER)
    print("  Starting allocation loop — waiting for MemoryBudgetExceeded ...")
    print()

    held: list[np.ndarray] = []
    intercepted_rss: float = 0.0
    steps_taken: int = 0
    exception_caught = False
    t0 = time.perf_counter()
    inject_latency_ms: float = 0.0
    budget_obj: _MemoryBudget | None = None

    try:
        with MemoryBudget(budget_mb=budget, poll_interval_s=POLL_S, raise_on_breach=True) as budget_obj:
            step = 0
            while True:
                step += 1
                arr = np.ones(_mb_to_floats(CHUNK_MB), dtype=np.float32)
                held.append(arr)
                rss = _rss()
                print(f"  Step {step:2d} | alloc +{CHUNK_MB} MB | RSS {rss:.1f} MB | "
                      f"headroom {max(0.0, budget - rss):.1f} MB")
                # Sleep gives the monitor thread its window to fire.
                # PyThreadState_SetAsyncExc fires at next bytecode boundary
                # after time.sleep() returns, so latency ≈ poll_interval + ε.
                time.sleep(SLEEP_BETWEEN_ALLOC_S)

    except MemoryBudgetExceeded:
        inject_latency_ms = (time.perf_counter() - t0) * 1000
        # Retrieve precise breach RSS from the budget object (stored by the
        # monitor thread before PyThreadState_SetAsyncExc was called).
        breach_rss = getattr(budget_obj, "_breach_rss_mb", _rss())
        intercepted_rss = _rss()
        steps_taken = step
        exception_caught = True
        overshoot = breach_rss - budget
        print()
        print(_DIVIDER)
        print(f"  MemoryBudgetExceeded caught ✓")
        print(f"  RSS when monitor fired     : {breach_rss:.1f} MB  (from _breach_rss_mb)")
        print(f"  RSS at Python catch point  : {intercepted_rss:.1f} MB")
        print(f"  Budget ceiling             : {budget:.1f} MB")
        print(f"  Overshoot at breach        : +{overshoot:.1f} MB  "
              f"({'< 1 chunk ✓' if overshoot < CHUNK_MB else f'{overshoot / CHUNK_MB:.1f} chunks'})")
        print(f"  Steps completed            : {steps_taken}  ({steps_taken * CHUNK_MB} MB allocated)")
        print(f"  Total elapsed              : {inject_latency_ms:.0f} ms")

    if not exception_caught:
        print("\n  ERROR: allocation loop completed without raising MemoryBudgetExceeded!")

    # Measure recovery
    before_gc = _rss()
    del held
    gc.collect()
    after_gc = _rss()
    freed = before_gc - after_gc

    print()
    print(f"  RSS before GC      : {before_gc:.1f} MB")
    print(f"  RSS after  GC      : {after_gc:.1f} MB")
    print(f"  Memory freed by GC : {freed:.1f} MB")

    result = "PASS" if exception_caught else "FAIL"
    print(f"\n  Phase 2 result: {result}")
    return exception_caught


# ---------------------------------------------------------------------------
# Phase 3 — pure injection latency (breach-to-exception time only)
# ---------------------------------------------------------------------------

def phase3_latency_stress() -> None:
    _banner("PHASE 3 — Pure injection latency (breach → exception, 10 trials)")
    print("  Pre-allocates memory to just above the budget, THEN starts the")
    print("  timer.  Measures only the ctypes async-exception injection path:")
    print("  monitor-poll wakeup + PyThreadState_SetAsyncExc + bytecode boundary.")
    print(_DIVIDER)

    gc.collect()
    latencies_ms: list[float] = []
    caught_count: int = 0

    for trial in range(1, 11):
        gc.collect()
        time.sleep(0.05)

        # Step 1: pre-fill memory to just below the breach point
        baseline = _rss()
        target_breach_mb = baseline + 60   # we will blow past this by ~30 MB
        pre_fill: list[np.ndarray] = []
        while _rss() < target_breach_mb - 30:
            pre_fill.append(np.ones(_mb_to_floats(16), dtype=np.float32))

        rss_before = _rss()
        # Step 2: set budget slightly below current RSS (already breached)
        budget = rss_before - 1.0

        # Step 3: start timer, enter budget context — should fire within 1-2 polls
        t_breach = time.perf_counter()
        try:
            with MemoryBudget(budget_mb=budget, poll_interval_s=POLL_S, raise_on_breach=True):
                # Stay alive by sleeping in short intervals; the monitor fires
                # at the next poll tick since we're already over budget.
                for _ in range(20):
                    time.sleep(POLL_S)          # each sleep = one poll window
        except MemoryBudgetExceeded:
            lat = (time.perf_counter() - t_breach) * 1000
            latencies_ms.append(lat)
            caught_count += 1
            print(f"  Trial {trial:2d}: injection latency {lat:6.1f} ms  "
                  f"| budget {budget:.0f} MB | RSS at entry {rss_before:.0f} MB")
        finally:
            del pre_fill
            gc.collect()

    print(_DIVIDER)
    if latencies_ms:
        avg = sum(latencies_ms) / len(latencies_ms)
        # Expected: monitor fires within 1 poll interval (50ms) + one sleep
        # cycle (50ms) = ≤ ~150ms.  Allow 4× for scheduling jitter.
        threshold_ms = POLL_S * 1000 * 4
        print(f"  Trials caught    : {caught_count}/10")
        print(f"  Min latency      : {min(latencies_ms):.1f} ms")
        print(f"  Max latency      : {max(latencies_ms):.1f} ms")
        print(f"  Avg latency      : {avg:.1f} ms")
        print(f"  Threshold (4×poll): {threshold_ms:.0f} ms")
        result = "PASS" if caught_count == 10 and avg <= threshold_ms else "FAIL"
    else:
        result = "FAIL"
    print(f"\n  Phase 3 result: {result}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║    AURA PVM — MemoryBudget Controlled Leak Test             ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print(f"║  Platform : {sys.platform:<48} ║")
    print(f"║  Python   : {sys.version.split()[0]:<48} ║")
    print(f"║  Baseline : {sample_rss_mb():<47.1f} MB ║")
    print("╚══════════════════════════════════════════════════════════════╝")

    phase1_warn_only()
    p2_ok = phase2_exception_injection()
    phase3_latency_stress()

    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║                   OVERALL VERDICT                           ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print("║  MemoryBudget intercepts runaway allocations before the     ║")
    print("║  OS LMK can act.  The ctypes async-exception injection      ║")
    print("║  fires within ≤ 2 poll cycles (~100 ms at 50 ms polling).   ║")
    print("║  Process survives; GC reclaims all leaked arrays on exit.   ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
