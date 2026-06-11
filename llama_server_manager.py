"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8b5-[Q-SYS:D4FAE19AB3EF864B]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit)
DEPENDENCIES: atexit, asyncio, signal, os, httpx, sys, __future__, subprocess, time
FUNCTIONS: __init__, _kill_orphans, start_server, async_start, terminate_server, is_alive, wait_for_ready, __repr__
SYNOPSIS: This Python module integrates `atexit`, `asyncio`, `signal`, `os`, `httpx`, `sys`, `subprocess`, and `time` to manage a server lifecycle with synchronous and asynchronous startup/shutdown controls via `__init__`, `_kill_orphans`, `start_server`, `async_start`, `terminate_server`, `is_alive`, `wait_for_ready`, and `__repr__`.
[/AURA_MASTER_KEY]
"""
from __future__ import annotations

import atexit
import asyncio
import os
import signal
import subprocess
import sys
import time

try:
    import httpx as _httpx
except (ImportError, RuntimeError, OSError):
    _httpx = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_PORT: int = 8081
_CONTEXT_LIMIT: int = 2048   # matched to Port 8081 context window c=2048
_BATCH_SIZE: int = 256        # -b 256 / -ub 256  (Termux 4 GB ceiling)
_WARMUP_SECONDS: float = 4.0  # model-weight-map settle time
_SHUTDOWN_TIMEOUT: float = 6.0


# ---------------------------------------------------------------------------
# LlamaServerManager
# ---------------------------------------------------------------------------

class LlamaServerManager:
    """
    Manages the background llama-server subprocess lifecycle.

    Key safety properties
    ---------------------
    1. Before startup, kills any existing llama-server process bound to
       *port* via ``pkill -f llama-server`` + ``fuser -k <port>/tcp``
       (prevents OSError: [Errno 98] Address already in use).

    2. Spawns the server in its own session (``start_new_session=True``)
       so ``os.killpg`` can terminate the full process group cleanly.

    3. Registers an ``atexit`` handler so the server is always stopped
       when the Python process exits — normally or via uncaught exception.

    4. ``terminate_server`` sends SIGTERM first, waits *_SHUTDOWN_TIMEOUT*
       seconds, then escalates to SIGKILL to ensure the port is freed.
    """

    def __init__(
        self,
        model_path: str,
        port: int = _DEFAULT_PORT,
        context_limit: int = _CONTEXT_LIMIT,
        batch_size: int = _BATCH_SIZE,
    ) -> None:
        self.model_path = model_path
        self.port = port
        self.context_limit = context_limit
        self.batch_size = batch_size
        self._process: subprocess.Popen | None = None
        atexit.register(self.terminate_server)

    # ------------------------------------------------------------------
    # Orphan cleanup
    # ------------------------------------------------------------------

    def _kill_orphans(self) -> None:
        """
        Kill any stale llama-server process bound to *port* before startup.
        Uses two independent mechanisms for robustness on Termux/Android:
        1. ``fuser -k <port>/tcp``  — kills by port binding
        2. ``pkill -f llama-server`` — kills by process name
        """
        try:
            subprocess.run(
                ["fuser", "-k", f"{self.port}/tcp"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        try:
            subprocess.run(
                ["pkill", "-f", "llama-server"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Brief pause so the kernel releases the socket descriptor
        time.sleep(0.3)

    # ------------------------------------------------------------------
    # Server startup
    # ------------------------------------------------------------------

    def start_server(self) -> bool:
        """
        Spawn llama-server with memory-constrained arguments.

        Parameters are clamped to the 4 GB Termux envelope:
          -c 2048   : context window
          -b 256    : batch size
          -ub 256   : ubatch size
        """
        if not os.path.exists(self.model_path):
            sys.stderr.write(
                f"[LlamaServerManager] Model not found: {self.model_path}\n"
            )
            return False

        self._kill_orphans()

        cmd = [
            "llama-server",
            "--model", self.model_path,
            "--port", str(self.port),
            "-c", str(self.context_limit),
            "-b", str(self.batch_size),
            "-ub", str(self.batch_size),
        ]

        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,   # isolates the process group
            )
            sys.stdout.write(
                f"[LlamaServerManager] Spawning llama-server "
                f"(PID {self._process.pid}) on port {self.port}…\n"
            )
            # Allow model weights to map into physical memory
            time.sleep(_WARMUP_SECONDS)
            if not self.is_alive():
                sys.stderr.write(
                    "[LlamaServerManager] Server exited immediately — "
                    "check model path and available RAM.\n"
                )
                return False
            sys.stdout.write(
                f"[LlamaServerManager] llama-server ready on port {self.port}.\n"
            )
            return True
        except FileNotFoundError:
            sys.stderr.write(
                "[LlamaServerManager] llama-server binary not found. "
                "Run setup.sh or install llama.cpp.\n"
            )
            return False
        except Exception as exc:
            sys.stderr.write(
                f"[LlamaServerManager] Failed to launch server: {exc}\n"
            )
            return False

    async def async_start(self) -> bool:
        """Non-blocking async wrapper — runs start_server in a thread."""
        return await asyncio.to_thread(self.start_server)

    # ------------------------------------------------------------------
    # Server shutdown
    # ------------------------------------------------------------------

    def terminate_server(self) -> None:
        """
        Graceful SIGTERM → timeout → SIGKILL sequence.
        Clears the port binding and releases physical RAM.
        """
        if self._process is None:
            return
        proc = self._process
        self._process = None

        try:
            pgid = os.getpgid(proc.pid)
        except ProcessLookupError:
            return

        try:
            os.killpg(pgid, signal.SIGTERM)
            proc.wait(timeout=_SHUTDOWN_TIMEOUT)
            sys.stdout.write(
                "[LlamaServerManager] llama-server process group terminated.\n"
            )
        except subprocess.TimeoutExpired:
            try:
                os.killpg(pgid, signal.SIGKILL)
                sys.stdout.write(
                    "[LlamaServerManager] SIGKILL sent after timeout.\n"
                )
            except ProcessLookupError:
                pass
        except ProcessLookupError:
            pass
        except Exception as exc:
            sys.stderr.write(
                f"[LlamaServerManager] Cleanup error: {exc}\n"
            )

    # ------------------------------------------------------------------
    # Status helpers
    # ------------------------------------------------------------------

    def is_alive(self) -> bool:
        """Return True if the server subprocess is still running."""
        return self._process is not None and self._process.poll() is None

    def wait_for_ready(self, timeout: float = 30.0, poll: float = 0.5) -> bool:
        """
        Poll the health endpoint until the server responds or *timeout* expires.
        Falls back to a simple process-alive check if httpx is unavailable.
        """
        if _httpx is not None:
            deadline = time.time() + timeout
            while time.time() < deadline:
                if not self.is_alive():
                    return False
                try:
                    resp = _httpx.get(
                        f"http://127.0.0.1:{self.port}/health",
                        timeout=1.0,
                    )
                    if resp.status_code == 200:
                        return True
                except Exception:
                    pass
                time.sleep(poll)
            return False
        else:
            # httpx not available — fall back to process liveness
            deadline = time.time() + timeout
            while time.time() < deadline:
                if self.is_alive():
                    return True
                time.sleep(poll)
            return False

    def __repr__(self) -> str:
        status = "alive" if self.is_alive() else "stopped"
        return (
            f"LlamaServerManager(port={self.port}, "
            f"context={self.context_limit}, status={status})"
        )
