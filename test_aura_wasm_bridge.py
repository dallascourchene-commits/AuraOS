from pathlib import Path
import textwrap

from aura_wasm_bridge import AuraRustWasmBridge, accelerator_runtime_status


def test_wasm_bridge_runs_stdio_accelerator(tmp_path: Path):
    fake = tmp_path / "fake_accel.py"
    fake.write_text(
        textwrap.dedent(
            """
            import json
            import sys

            envelope = json.loads(sys.stdin.read())
            raw = bytes.fromhex(envelope["payload_hex"]).decode("utf-8")
            compressed = raw.replace(" ", "")
            print(json.dumps({
                "status": "success",
                "accelerator": "rust:fake",
                "operation": envelope["operation"],
                "compressed_hex": compressed.encode("utf-8").hex(),
            }))
            """
        ).strip(),
        encoding="utf-8",
    )

    result = AuraRustWasmBridge(fake).accelerate("alpha beta gamma", "text")

    assert result is not None
    assert result.compressed_payload == "alphabetagamma"
    assert result.accelerator == "rust:fake"
    assert result.operation == "crush_text"


def test_runtime_status_reports_python_fallback(monkeypatch):
    monkeypatch.setenv("AURA_CRUSH_ACCELERATOR", "python")

    status = accelerator_runtime_status()

    assert status["enabled"] is False
    assert status["runtime"] == "python"


def test_auto_discovery_ignores_bare_worktree_binary(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("AURA_CRUSH_ACCELERATOR", raising=False)
    monkeypatch.delenv("AURA_CRUSH_ACCELERATOR_PATH", raising=False)
    monkeypatch.delenv("AURA_CRUSH_WASM", raising=False)
    monkeypatch.delenv("AURA_WASM_ACCELERATOR", raising=False)
    bare = tmp_path / "aura_crush_core"
    bare.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")

    bridge = AuraRustWasmBridge.from_env(root=tmp_path)

    assert bridge.enabled is False


def test_explicit_env_path_allows_non_aura_memory_accelerator(monkeypatch, tmp_path: Path):
    explicit = tmp_path / "aura_crush_core"
    explicit.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    monkeypatch.setenv("AURA_CRUSH_ACCELERATOR_PATH", str(explicit))

    bridge = AuraRustWasmBridge.from_env(root=tmp_path)

    assert bridge.enabled is True
    assert bridge.accelerator_path == explicit
