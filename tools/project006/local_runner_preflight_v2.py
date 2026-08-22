"""Minimal read-only WP10 host probe for a real self-hosted Aura runner.

This file intentionally does *not* dispatch provider work. It proves or blocks
local WSL/Resident/socket/provider prerequisites without reading secret values.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import stat
import subprocess
import sys
import time
from typing import Any

SCHEMA = "WP10LocalRunnerPreflightReceiptV1"
UNIT = "aura-project006.service"
RESIDENT_SOURCE = Path("/home/john_of_wick/.local/lib/aura/project006/aura_resident_service.py")
PROVIDER_SOURCE = Path("tools/project006/provider_sidecar_reference/provider_sidecar.py")
HANDOFF_SOURCE = Path("tools/project006/provider_sidecar_reference/provider_handoff.py")


def _digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file(path: Path) -> dict[str, Any]:
    out: dict[str, Any] = {"path": str(path), "exists": False, "sha256": None}
    try:
        resolved = path.expanduser().resolve(strict=True)
        st = resolved.stat()
        out.update(
            path=str(resolved),
            exists=True,
            sha256=_digest_bytes(resolved.read_bytes()),
            size=st.st_size,
            uid=st.st_uid,
            mode=oct(stat.S_IMODE(st.st_mode)),
        )
    except (OSError, PermissionError):
        pass
    return out


def _systemd() -> dict[str, Any]:
    properties = (
        "LoadState",
        "ActiveState",
        "SubState",
        "MainPID",
        "FragmentPath",
        "RuntimeDirectory",
    )
    argv = [
        "systemctl",
        "--user",
        "show",
        UNIT,
        "--no-pager",
        *[f"--property={name}" for name in properties],
    ]
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", ""),
        "XDG_RUNTIME_DIR": os.environ.get("XDG_RUNTIME_DIR", ""),
        "DBUS_SESSION_BUS_ADDRESS": os.environ.get("DBUS_SESSION_BUS_ADDRESS", ""),
    }
    try:
        p = subprocess.run(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=10,
            check=False,
            env=env,
        )
    except (OSError, subprocess.SubprocessError):
        return {"query_ok": False, "unit": UNIT}
    values: dict[str, str] = {}
    if p.returncode == 0:
        for line in p.stdout.splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                values[key] = value
    try:
        pid = int(values.get("MainPID", "0"))
    except ValueError:
        pid = 0
    fragment = values.get("FragmentPath") or None
    return {
        "query_ok": p.returncode == 0,
        "unit": UNIT,
        "load_state": values.get("LoadState") or "UNKNOWN",
        "active_state": values.get("ActiveState") or "UNKNOWN",
        "sub_state": values.get("SubState") or "UNKNOWN",
        "main_pid": pid if pid > 0 else None,
        "fragment_path": fragment,
        "unit_file_identity": _file(Path(fragment)) if fragment else None,
        "runtime_directory": values.get("RuntimeDirectory") or None,
    }


def _process(pid: int | None) -> dict[str, Any]:
    if not pid:
        return {"pid": None, "alive": False, "exe": None, "cmdline_sha256": None}
    root = Path("/proc") / str(pid)
    out: dict[str, Any] = {"pid": pid, "alive": root.exists(), "exe": None, "cmdline_sha256": None}
    if not root.exists():
        return out
    try:
        out["exe"] = os.readlink(root / "exe")
    except OSError:
        pass
    try:
        # Command arguments are never emitted because they may contain secrets.
        out["cmdline_sha256"] = _digest_bytes((root / "cmdline").read_bytes())
    except OSError:
        pass
    return out


def _wsl() -> dict[str, Any]:
    distro = os.environ.get("WSL_DISTRO_NAME")
    try:
        version = Path("/proc/version").read_text(encoding="utf-8", errors="replace")
    except OSError:
        version = ""
    return {
        "is_wsl": bool(distro or "microsoft" in version.lower()),
        "distro": distro or None,
        "kernel_release": platform.release(),
        "machine": platform.machine(),
    }


def _socket(runtime_directory: str | None) -> dict[str, Any]:
    xdg = os.environ.get("XDG_RUNTIME_DIR")
    roots: list[Path] = []
    if xdg and runtime_directory:
        roots.extend(Path(xdg) / part for part in runtime_directory.split() if part)
    if xdg:
        roots.append(Path(xdg))
    candidates: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        try:
            for item in root.rglob("*"):
                try:
                    if stat.S_ISSOCK(item.stat().st_mode):
                        name = item.name.lower()
                        if any(t in name for t in ("aura", "resident", "project006", ".sock")):
                            candidates.append(item.resolve())
                except OSError:
                    continue
        except OSError:
            continue
    unique = sorted({str(p) for p in candidates})
    if len(unique) != 1:
        return {"path": None, "exists": False, "is_socket": False, "candidate_count": len(unique)}
    path = Path(unique[0])
    try:
        st = path.stat()
    except OSError:
        return {"path": str(path), "exists": False, "is_socket": False, "candidate_count": 1}
    return {
        "path": str(path),
        "exists": True,
        "is_socket": stat.S_ISSOCK(st.st_mode),
        "uid": st.st_uid,
        "gid": st.st_gid,
        "mode": oct(stat.S_IMODE(st.st_mode)),
        "candidate_count": 1,
    }


def _credential_presence() -> dict[str, str]:
    # Never serialize, hash, print, or otherwise expose the value.
    if os.environ.get("DEEPSEEK_API_KEY"):
        return {"state": "PRESENT", "source_class": "ENVIRONMENT_NAME_ONLY"}
    try:
        from aura_api_rotator import load_secrets, provider_key_pool
        pool = tuple(provider_key_pool("deepseek", load_secrets()))
    except Exception:
        return {"state": "UNKNOWN", "source_class": "UNAVAILABLE"}
    return {
        "state": "PRESENT" if pool else "ABSENT",
        "source_class": "AURA_API_ROTATOR_NONSECRET_PRESENCE_ONLY",
    }


def main() -> int:
    observed_ms = int(time.time() * 1000)
    wsl = _wsl()
    service = _systemd()
    process = _process(service.get("main_pid"))
    resident = _file(RESIDENT_SOURCE)
    provider = _file(PROVIDER_SOURCE)
    handoff = _file(HANDOFF_SOURCE)
    socket = _socket(service.get("runtime_directory"))
    credential = _credential_presence()

    blockers: list[dict[str, str]] = []
    def block(code: str, detail: str) -> None:
        blockers.append({"code": code, "detail": detail})

    if not wsl["is_wsl"]:
        block("P1_NOT_WSL", "self-hosted runner is not executing inside WSL")
    if not service.get("query_ok"):
        block("P1_SYSTEMD_QUERY_FAILED", "cannot query WSL user systemd")
    if service.get("load_state") != "loaded":
        block("P2_RESIDENT_UNIT_NOT_LOADED", str(service.get("load_state")))
    if service.get("active_state") != "active":
        block("P2_RESIDENT_NOT_ACTIVE", str(service.get("active_state")))
    if not process.get("alive"):
        block("P2_RESIDENT_PROCESS_MISSING", "MainPID absent or dead")
    if not resident.get("sha256"):
        block("P2_RESIDENT_SOURCE_UNBOUND", str(RESIDENT_SOURCE))
    if not socket.get("is_socket"):
        block("P2_RESIDENT_SOCKET_UNBOUND", f"candidate_count={socket.get('candidate_count')}")
    if not provider.get("sha256"):
        block("P3_PROVIDER_SOURCE_UNBOUND", str(PROVIDER_SOURCE))
    if not handoff.get("sha256"):
        block("P3_PROVIDER_HANDOFF_UNBOUND", str(HANDOFF_SOURCE))
    if credential["state"] != "PRESENT":
        block("P3_DEEPSEEK_CREDENTIAL_NOT_PRESENT", credential["state"])

    local_ok = not blockers
    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "preflight_id": f"wp10-local-runtime-{observed_ms}",
        "observed_at_local_ms": observed_ms,
        "effect_time_basis": "SELF_HOSTED_LOCAL_OBSERVATION_V1",
        "control_surface_identity": {
            "python": sys.version.split()[0],
            "platform": platform.system(),
            "uid": os.getuid() if hasattr(os, "getuid") else None,
        },
        "wsl_context_identity": wsl,
        "resident_service_unit_identity": service,
        "service_state": service.get("active_state"),
        "installed_resident_source_identity": resident,
        "resident_process_identity": process,
        "resident_socket_path": socket.get("path"),
        "resident_socket_protection_evidence": socket,
        "provider_sidecar_source_identity": provider,
        "provider_sidecar_process_identity": "ON_DEMAND_PROVIDER_HANDOFF_PROCESS",
        "provider_sidecar_config_identity": handoff,
        "provider_route_owner_ref": "aura_provider_registry:deepseek",
        "provider_credential_presence_state": credential["state"],
        "provider_credential_source_class": credential["source_class"],
        "provider_egress_confinement_state": "PROVIDER_SIDECAR_ONLY" if provider.get("sha256") and handoff.get("sha256") else "UNKNOWN",
        "local_runtime_observation_state": "PASS_LOCAL_RUNTIME_SURFACE" if local_ok else "BLOCKED_LOCAL_RUNTIME_SURFACE",
        "blockers": blockers,
        # This probe never launders local health into full bridge admission. The
        # source-owned WP02-WP09 package must be rebound separately at effect time.
        "ready_state": "BLOCKED_REVIEW" if local_ok else "BLOCKED_LOCAL_SOURCE",
        "source_package_revalidation_required": True,
        "no_secret_log_attestation": True,
    }
    preimage = dict(receipt)
    receipt["receipt_digest"] = _digest_bytes(
        json.dumps(preimage, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    )
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    return 0 if local_ok else 4


if __name__ == "__main__":
    raise SystemExit(main())
