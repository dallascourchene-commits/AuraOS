"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8fd-[Q-SYS:WASM_ACCELERATOR_BRIDGE]
DIKWP_TIER: PURPOSE
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Integrity / Sandboxed Native Acceleration)
DEPENDENCIES: dataclasses, json, os, pathlib, shutil, subprocess, sys, time, typing
FUNCTIONS: WasmAccelerationResult, AuraRustWasmBridge, accelerator_runtime_status
SYNOPSIS: Optional Rust/WASI bridge for Aura native accelerators. Executes local stdin/stdout accelerators without daemons or network sockets, prefers explicit environment configuration, and degrades to Python when no accelerator is available.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any


DEFAULT_ACCELERATOR_NAMES = (
    "Aura_Memory/aura_crush_core.cwasm",
    "Aura_Memory/aura_crush_core.wasm",
    "Aura_Memory/aura_crush_core",
    "Aura_Memory/aura_crush_core.exe",
)

_OPERATION_BY_CONTENT_TYPE = {
    "json": "crush_json",
    "log": "crush_log",
    "search": "crush_text",
    "diff": "crush_text",
    "text": "crush_text",
}


@dataclass(frozen=True)
class WasmAccelerationResult:
    compressed_payload: str
    accelerator: str
    operation: str
    latency_sec: float
    warnings: tuple[str, ...] = ()

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "accelerator": self.accelerator,
            "operation": self.operation,
            "compressed_chars": len(self.compressed_payload),
            "latency_sec": round(self.latency_sec, 6),
            "warnings": list(self.warnings),
        }


class AuraRustWasmBridge:
    """Run a local Rust native or WASI accelerator using Aura's JSON stdio contract."""

    def __init__(
        self,
        accelerator_path: str | Path | None = None,
        *,
        timeout_sec: float = 2.0,
        wasmtime_bin: str | None = None,
    ) -> None:
        self.accelerator_path = Path(accelerator_path).expanduser() if accelerator_path else None
        self.timeout_sec = max(0.05, float(timeout_sec))
        self.wasmtime_bin = wasmtime_bin

    @classmethod
    def from_env(cls, *, root: str | Path | None = None) -> "AuraRustWasmBridge":
        mode = os.environ.get("AURA_CRUSH_ACCELERATOR", "auto").strip().lower()
        if mode in {"0", "false", "off", "disabled", "python"}:
            return cls(None)

        explicit = (
            os.environ.get("AURA_CRUSH_ACCELERATOR_PATH")
            or os.environ.get("AURA_CRUSH_WASM")
            or os.environ.get("AURA_WASM_ACCELERATOR")
        )
        if explicit:
            return cls(explicit)

        base = Path(root or os.getcwd())
        for name in DEFAULT_ACCELERATOR_NAMES:
            candidate = (base / name).resolve()
            if candidate.exists():
                return cls(candidate)
        return cls(None)

    @property
    def enabled(self) -> bool:
        return self.accelerator_path is not None and self.accelerator_path.exists()

    def accelerate(self, raw_content: str, content_type: str) -> WasmAccelerationResult | None:
        if not self.enabled or not raw_content:
            return None
        operation = _OPERATION_BY_CONTENT_TYPE.get(content_type)
        if operation is None:
            return None

        command = self._command()
        if not command:
            return None

        envelope = {
            "version": "AURA_WASM_BRIDGE_V1",
            "operation": operation,
            "payload_hex": raw_content.encode("utf-8", errors="replace").hex(),
        }
        start = time.time()
        try:
            proc = subprocess.run(
                command,
                input=json.dumps(envelope, separators=(",", ":")),
                capture_output=True,
                text=True,
                timeout=self.timeout_sec,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None

        if proc.returncode != 0:
            return None

        try:
            payload = json.loads(proc.stdout.strip() or "{}")
            compressed_hex = str(payload.get("compressed_hex") or "")
            compressed = bytes.fromhex(compressed_hex).decode("utf-8", errors="replace")
        except (json.JSONDecodeError, TypeError, ValueError):
            return None

        if payload.get("status") != "success" or not compressed:
            return None

        return WasmAccelerationResult(
            compressed_payload=compressed,
            accelerator=str(payload.get("accelerator") or self._accelerator_label()),
            operation=str(payload.get("operation") or operation),
            latency_sec=time.time() - start,
            warnings=tuple(str(item) for item in payload.get("warnings", []) if item),
        )

    def _command(self) -> list[str] | None:
        if self.accelerator_path is None:
            return None
        suffix = self.accelerator_path.suffix.lower()
        path = str(self.accelerator_path)
        if suffix in {".wasm", ".cwasm"}:
            wasmtime = (
                self.wasmtime_bin
                or os.environ.get("AURA_WASMTIME_BIN")
                or shutil.which("wasmtime")
            )
            if not wasmtime:
                return None
            if suffix == ".cwasm":
                return [wasmtime, "--allow-precompiled", path]
            return [wasmtime, path]
        if suffix == ".py":
            return [sys.executable, path]
        return [path]

    def _accelerator_label(self) -> str:
        if self.accelerator_path is None:
            return "disabled"
        suffix = self.accelerator_path.suffix.lower()
        if suffix in {".wasm", ".cwasm"}:
            return "rust-wasm:aura_crush_core"
        return "rust-native:aura_crush_core"


def accelerator_runtime_status(root: str | Path | None = None) -> dict[str, Any]:
    bridge = AuraRustWasmBridge.from_env(root=root)
    path = str(bridge.accelerator_path) if bridge.accelerator_path else ""
    suffix = bridge.accelerator_path.suffix.lower() if bridge.accelerator_path else ""
    return {
        "enabled": bridge.enabled,
        "path": path,
        "runtime": "wasmtime" if suffix in {".wasm", ".cwasm"} else ("native" if path else "python"),
        "wasmtime_available": bool(shutil.which(os.environ.get("AURA_WASMTIME_BIN", "wasmtime"))),
    }
