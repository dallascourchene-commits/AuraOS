from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "pvm_memory_guard.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "import sys\nimport time\n",
        "import sys\nimport time\nimport threading\nimport ctypes\n",
        "imports",
    )
    text = replace_once(
        text,
        '''        self.raise_on_breach = raise_on_breach\n        self._stop_event = asyncio.Event() if asyncio else None\n        self._task: object | None = None  # asyncio.Task\n        self._breached = False\n''',
        '''        self.raise_on_breach = raise_on_breach\n        self._stop_event = threading.Event()\n        self._task: object | None = None  # asyncio.Task\n        self._thread: threading.Thread | None = None\n        self._main_thread_id: int | None = None\n        self._breached = False\n''',
        "initializer",
    )
    text = replace_once(
        text,
        '''    def __enter__(self) -> MemoryBudget:\n        self._stop_event.clear()\n        # Pure-asyncio: launch monitor as a background task\n        try:\n            loop = asyncio.get_running_loop()\n        except RuntimeError:\n            loop = None\n        if loop is not None and asyncio is not None:\n            self._task = loop.create_task(self._monitor_loop_async())\n        else:\n            # Fallback for synchronous call sites (rare in Termux)\n            self._monitor_loop_sync()\n        return self\n\n    def __exit__(self, *_: object) -> None:\n        self._stop_event.set()\n        if self._task is not None:\n            try:\n                self._task.cancel()\n            except Exception:\n                pass\n''',
        '''    def __enter__(self) -> MemoryBudget:\n        self._stop_event.clear()\n        self._main_thread_id = threading.get_ident()\n        try:\n            loop = asyncio.get_running_loop() if asyncio is not None else None\n        except RuntimeError:\n            loop = None\n        if loop is not None:\n            self._task = loop.create_task(self._monitor_loop_async())\n        else:\n            # Synchronous callers still need monitoring while the with-block is\n            # executing.  Run the monitor concurrently instead of blocking\n            # __enter__ for the five-minute fallback deadline.\n            self._thread = threading.Thread(\n                target=self._monitor_loop_sync,\n                name="AuraMemoryBudgetMonitor",\n                daemon=True,\n            )\n            self._thread.start()\n        return self\n\n    def __exit__(self, *_: object) -> None:\n        self._stop_event.set()\n        if self._task is not None:\n            try:\n                self._task.cancel()\n            except Exception:\n                pass\n        if self._thread is not None and self._thread is not threading.current_thread():\n            self._thread.join(timeout=max(1.0, self.poll_interval_s * 2.0))\n            self._thread = None\n''',
        "context protocol",
    )
    text = replace_once(
        text,
        '''    def _monitor_loop_sync(self) -> None:\n        """Synchronous fallback (no event loop available)."""\n        deadline = time.monotonic() + 300  # 5-minute max guard\n        while not self._stop_event.is_set() and time.monotonic() < deadline:\n            current = sample_rss_mb()\n            if current > self.budget_mb:\n                self._breached = True\n                msg = (\n                    f"[PVM MEMORY GUARD] RSS {current:.1f} MB exceeds "\n                    f"budget {self.budget_mb:.1f} MB."\n                )\n                print(msg, file=sys.stderr, flush=True)\n                break\n            time.sleep(self.poll_interval_s)\n\n    def _raise_in_main_thread(self, current_mb: float) -> None:\n        """\n        Legacy mechanism — deprecated in pure-asyncio mode.\n        Stores breach data for inspection by the caller.\n        """\n        exc = MemoryBudgetExceeded(current_mb, self.budget_mb)\n        self._pending_exc = exc\n        self._breach_rss_mb = current_mb\n''',
        '''    def _monitor_loop_sync(self) -> None:\n        """Background monitor used by synchronous context-manager callers."""\n        deadline = time.monotonic() + 300\n        while not self._stop_event.is_set() and time.monotonic() < deadline:\n            current = sample_rss_mb()\n            if current > self.budget_mb:\n                self._breached = True\n                msg = (\n                    f"[PVM MEMORY GUARD] RSS {current:.1f} MB exceeds "\n                    f"budget {self.budget_mb:.1f} MB."\n                )\n                print(msg, file=sys.stderr, flush=True)\n                if self.raise_on_breach:\n                    self._raise_in_main_thread(current)\n                break\n            self._stop_event.wait(self.poll_interval_s)\n\n    def _raise_in_main_thread(self, current_mb: float) -> None:\n        """Inject ``MemoryBudgetExceeded`` into the synchronous owner thread."""\n        self._pending_exc = MemoryBudgetExceeded(current_mb, self.budget_mb)\n        self._breach_rss_mb = current_mb\n        thread_id = self._main_thread_id\n        if thread_id is None:\n            return\n        result = ctypes.pythonapi.PyThreadState_SetAsyncExc(\n            ctypes.c_ulong(thread_id), ctypes.py_object(MemoryBudgetExceeded)\n        )\n        if result > 1:\n            ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_ulong(thread_id), None)\n            raise RuntimeError("failed to inject MemoryBudgetExceeded safely")\n''',
        "sync monitor",
    )
    TARGET.write_text(text, encoding="utf-8")
    print("WC-02 synchronous MemoryBudget monitor repair applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
