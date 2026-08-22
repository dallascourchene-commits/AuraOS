"""Read-only Project006 local-runtime preflight probe.

Produces the non-secret runtime witness required by the WP10
``WP10LocalRunnerPreflightReceiptV1`` contract.  This module observes the local
WSL/systemd/Resident/provider surfaces only; it does not start, stop, reload,
install, dispatch, mutate Drive, or call a provider.

The probe is intentionally fail-closed.  Missing or ambiguous local facts stay
UNKNOWN/BLOCKED rather than being inferred from Drive or repository state.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import stat
import subprocess
import sys
import time
from typing import Any, Callable, Mapping, Sequence

SCHEMA = "WP10LocalRunnerPreflightReceiptV1"
CANONICAL_PROFILE = "WP10_LOCAL_PREFLIGHT_CANONICAL_JSON_V1"
DEFAULT_UNIT = "aura-project006.service"
DEFAULT_RESIDENT_SOURCE = "/home/john_of_wick/.local/lib/aura/project006/aura_resident_service.py"
DEFAULT_PROVIDER_SOURCE = "tools/project006/provider_sidecar_reference/provider_sidecar.py"
DEFAULT_HANDOFF_SOURCE = "tools/project006/provider_sidecar_reference/provider_handoff.py"

READY = "READY_FOR_BOUNDED_EXECUTION"
BLOCKED_LOCAL = "BLOCKED_LOCAL_SOURCE"
BLOCKED_RUNTIME = "BLOCKED_RUNTIME_BINDING"
BLOCKED_PROVIDER = "BLOCKED_PROVIDER"
BLOCKED_REVIEW = "BLOCKED_REVIEW"

Runner = Callable[[Sequence[str]], tuple[int, str, str]]


def _run(argv: Sequence[str]) -> tuple[int, str, str]:
    completed = subprocess.run(
        list(argv),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=10,
        check=False,
        env={
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": os.environ.get("HOME", ""),
            "XDG_RUNTIME_DIR": os.environ.get("XDG_RUNTIME_DIR", ""),
            "DBUS_SESSION_BUS_ADDRESS": os.environ.get("DBUS_SESSION_BUS_ADDRESS", ""),
        },
    )
    return completed.returncode, completed.stdout, completed.stderr


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str | None:
    try:
        with path.open("rb") as fh:
            digest = hashlib.sha256()
            while True:
                block = fh.read(1024 * 1024)
                if not block:
                    return digest.hexdigest()
                digest.update(block)
    except (OSError, PermissionError):
        return None


def _canonical_digest(value: Mapping[str, Any]) -> str:
    body = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return _sha256_bytes(body)


def _file_identity(path: Path) -> dict[str, Any]:
    identity: dict[str, Any] = {"path": str(path), "exists": False, "sha256": None}
    try:
        resolved = path.expanduser().resolve(strict=True)
        info = resolved.stat()
    except (OSError, PermissionError):
        return identity
    identity.update(
        {
            "path": str(resolved),
            "exists": True,
            "sha256": _sha256_file(resolved),
            "size": info.st_size,
            "mode": oct(stat.S_IMODE(info.st_mode)),
            "uid": info.st_uid,
        }
    )
    return identity


def _systemd_properties(unit: str, runner: Runner) -> dict[str, Any]:
    props = [
        "LoadState",
        "ActiveState",
        "SubState",
        "MainPID",
        "FragmentPath",
        "RuntimeDirectory",
        "User",
    ]
    rc, stdout, _ = runner(
        ["systemctl", "--user", "show", unit, "--no-pager", *[f"-p={p}" for p in props]]
    )
    result: dict[str, Any] = {
        "unit": unit,
        "query_ok": rc == 0,
        "load_state": "UNKNOWN",
        "active_state": "UNKNOWN",
        "sub_state": "UNKNOWN",
        "main_pid": None,
        "fragment_path": None,
        "runtime_directory": None,
        "service_user": None,
    }
    if rc != 0:
        return result
    values: dict[str, str] = {}
    for line in stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    result.update(
        {
            "load_state": values.get("LoadState") or "UNKNOWN",
            "active_state": values.get("ActiveState") or "UNKNOWN",
            "sub_state": values.get("SubState") or "UNKNOWN",
            "fragment_path": values.get("FragmentPath") or None,
            "runtime_directory": values.get("RuntimeDirectory") or None,
            "service_user": values.get("User") or None,
        }
    )
    try:
        pid = int(values.get("MainPID", "0"))
    except ValueError:
        pid = 0
    result["main_pid"] = pid if pid > 0 else None
    if result["fragment_path"]:
        result["unit_file_identity"] = _file_identity(Path(result["fragment_path"]))
    else:
        result["unit_file_identity"] = None
    return result


def _process_identity(pid: int | None) -> dict[str, Any]:
    if not pid:
        return {"pid": None, "alive": False, "exe": None, "cmdline_sha256": None}
    proc = Path("/proc") / str(pid)
    result: dict[str, Any] = {"pid": pid, "alive": proc.exists(), "exe": None, "cmdline_sha256": None}
    if not proc.exists():
        return result
    try:
        result["exe"] = os.readlink(proc / "exe")
    except OSError:
        pass
    try:
        # Hash only.  Arguments can contain secrets and are never serialized.
        result["cmdline_sha256"] = _sha256_bytes((proc / "cmdline").read_bytes())
    except OSError:
        pass
    return result


def _wsl_identity() -> dict[str, Any]:
    distro = os.environ.get("WSL_DISTRO_NAME")
    try:
        proc_version = Path("/proc/version").read_text(encoding="utf-8", errors="replace")
    except OSError:
        proc_version = ""
    is_wsl = bool(distro or "microsoft" in proc_version.lower())
    return {
        "is_wsl": is_wsl,
        "distro": distro or None,
        "kernel_release": platform.release(),
        "machine": platform.machine(),
    }


def _socket_identity(path_text: str | None) -> dict[str, Any]:
    if not path_text:
        return {"path": None, "exists": False, "is_socket": False}
    path = Path(path_text).expanduser()
    result: dict[str, Any] = {"path": str(path), "exists": False, "is_socket": False}
    try:
        info = path.stat()
    except OSError:
        return result
    result.update(
        {
            "path": str(path.resolve()),
            "exists": True,
            "is_socket": stat.S_ISSOCK(info.st_mode),
            "uid": info.st_uid,
            "gid": info.st_gid,
            "mode": oct(stat.S_IMODE(info.st_mode)),
        }
    )
    return result


def _discover_socket(explicit: str | None, runtime_directory: str | None) -> str | None:
    if explicit:
        return explicit
    xdg = os.environ.get("XDG_RUNTIME_DIR")
    roots: list[Path] = []
    if runtime_directory and xdg:
        # RuntimeDirectory from a user unit is a name beneath XDG_RUNTIME_DIR.
        roots.extend(Path(xdg) / part for part in runtime_directory.split() if part)
    if xdg:
        roots.append(Path(xdg))
    candidates: list[str] = []
    for root in roots:
        try:
            for item in root.glob("**/*"):
                if len(item.parts) - len(root.parts) > 3:
                    continue
                name = item.name.lower()
                if not any(token in name for token in ("aura", "resident", "project006", ".sock")):
                    continue
                try:
                    if stat.S_ISSOCK(item.stat().st_mode):
                        candidates.append(str(item.resolve()))
                except OSError:
                    continue
        except OSError:
            continue
    unique = sorted(set(candidates))
    return unique[0] if len(unique) == 1 else None


def _credential_presence() -> dict[str, Any]:
    # Values are never copied, hashed, logged, or serialized.
    env_present = bool(os.environ.get("DEEPSEEK_API_KEY"))
    if env_present:
        return {"state": "PRESENT", "source_class": "ENVIRONMENT_NAME_ONLY"}
    try:
        from aura_api_rotator import load_secrets, provider_key_pool

        pool = tuple(provider_key_pool("deepseek", load_secrets()))
        return {
            "state": "PRESENT" if pool else "ABSENT",
            "source_class": "AURA_API_ROTATOR_NONSECRET_PRESENCE_ONLY",
        }
    except Exception:
        return {"state": "UNKNOWN", "source_class": "UNAVAILABLE"}


def _load_package_state(path: str | None) -> dict[str, Any]:
    names = ("wp02", "wp03", "wp05", "wp06", "wp07", "wp08", "wp09")
    default = {f"{name}_identity": None for name in names}
    default.update({f"{name}_state": "UNKNOWN" for name in names})
    if not path:
        return default
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default
    if not isinstance(raw, dict):
        return default
    result = dict(default)
    for key in result:
        value = raw.get(key)
        if value is None or isinstance(value, (str, int, float, bool)):
            result[key] = value
    return result


def collect_preflight(
    *,
    unit: str = DEFAULT_UNIT,
    resident_source: str = DEFAULT_RESIDENT_SOURCE,
    provider_source: str = DEFAULT_PROVIDER_SOURCE,
    handoff_source: str = DEFAULT_HANDOFF_SOURCE,
    socket_path: str | None = None,
    package_state_file: str | None = None,
    runner: Runner = _run,
    now_ms: int | None = None,
) -> dict[str, Any]:
    observed_ms = int(time.time() * 1000) if now_ms is None else now_ms
    wsl = _wsl_identity()
    service = _systemd_properties(unit, runner)
    process = _process_identity(service.get("main_pid"))
    resident = _file_identity(Path(resident_source))
    provider = _file_identity(Path(provider_source))
    handoff = _file_identity(Path(handoff_source))
    socket = _socket_identity(
        _discover_socket(socket_path, service.get("runtime_directory"))
    )
    credential = _credential_presence()
    package = _load_package_state(package_state_file)

    blockers: list[dict[str, str]] = []

    def block(code: str, source: str, detail: str) -> None:
        blockers.append({"code": code, "source": source, "detail": detail})

    if not wsl["is_wsl"]:
        block("P1_NOT_WSL", "local:/proc/version", "WSL context not established")
    if not service["query_ok"]:
        block("P1_SYSTEMD_QUERY_FAILED", f"systemd:{unit}", "user-unit query failed")
    elif service["load_state"] != "loaded":
        block("P2_RESIDENT_UNIT_NOT_LOADED", f"systemd:{unit}", str(service["load_state"]))
    if service["active_state"] != "active":
        block("P2_RESIDENT_NOT_ACTIVE", f"systemd:{unit}", str(service["active_state"]))
    if not process["alive"]:
        block("P2_RESIDENT_PROCESS_MISSING", f"systemd:{unit}", "MainPID is absent/dead")
    if not resident["exists"] or not resident.get("sha256"):
        block("P2_RESIDENT_SOURCE_UNBOUND", resident_source, "installed Resident source unreadable")
    if not socket["exists"] or not socket["is_socket"]:
        block("P2_RESIDENT_SOCKET_UNBOUND", socket.get("path") or "runtime-dir", "unique live AF_UNIX socket not established")
    if not provider["exists"] or not provider.get("sha256"):
        block("P3_PROVIDER_SOURCE_UNBOUND", provider_source, "provider sidecar source unreadable")
    if not handoff["exists"] or not handoff.get("sha256"):
        block("P3_PROVIDER_HANDOFF_UNBOUND", handoff_source, "governed provider handoff source unreadable")
    if credential["state"] != "PRESENT":
        block("P3_DEEPSEEK_CREDENTIAL_NOT_PRESENT", "local:credential-presence", credential["state"])

    package_states = [package[f"{name}_state"] for name in ("wp02", "wp03", "wp05", "wp06", "wp07", "wp08", "wp09")]
    if any(state in (None, "UNKNOWN", "BLOCKED", "REPAIR", "REVIEW_REQUIRED") for state in package_states):
        block("P4_P10_SOURCE_PACKAGE_NOT_ADMITTED", "package-state-file", "one or more source-owned package states are not admitted/current")

    if any(item["code"].startswith("P1_") for item in blockers):
        ready_state = BLOCKED_LOCAL
    elif any(item["code"].startswith("P2_") for item in blockers):
        ready_state = BLOCKED_RUNTIME
    elif any(item["code"].startswith("P3_") for item in blockers):
        ready_state = BLOCKED_PROVIDER
    elif blockers:
        ready_state = BLOCKED_REVIEW
    else:
        ready_state = READY

    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "canonical_profile": CANONICAL_PROFILE,
        "preflight_id": f"wp10-local-{observed_ms}",
        "observed_at_local_ms": observed_ms,
        "effect_time_basis": "LOCAL_MONOTONIC_OBSERVATION_WINDOW_V1",
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
        "resident_reference_profile_identity": "PROJECT006_LANE_A_G9_SOURCE_CONTRACT",
        "installed_profile_identity": resident.get("sha256"),
        "adoption_state": "OBSERVED_INSTALLED_SOURCE_UNREVIEWED_BINDING" if resident.get("sha256") else "UNKNOWN",
        "resident_generation": "UNKNOWN",
        "currentness_ref": "UNKNOWN",
        "authority_ref": "UNKNOWN",
        "resident_state_source_witness": "systemd+installed-source",
        "rollback_anchor_identity": service.get("unit_file_identity"),
        "local_modification_state": "UNKNOWN",
        "provider_sidecar_source_identity": provider,
        "provider_sidecar_process_identity": "ON_DEMAND_PROVIDER_HANDOFF_PROCESS",
        "provider_sidecar_config_identity": handoff,
        "provider_route_owner_ref": "aura_provider_registry:deepseek",
        "route_model_capability_witness": {
            "sidecar_source_present": bool(provider.get("sha256")),
            "handoff_source_present": bool(handoff.get("sha256")),
        },
        "provider_credential_presence_state": credential["state"],
        "provider_credential_source_class": credential["source_class"],
        "provider_egress_confinement_state": "PROVIDER_SIDECAR_ONLY" if provider.get("sha256") and handoff.get("sha256") else "UNKNOWN",
        **package,
        "blockers": blockers,
        "ready_state": ready_state,
        "no_secret_log_attestation": True,
    }
    receipt["receipt_digest"] = _canonical_digest(receipt)
    return receipt


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Emit a non-secret Project006 WP10 local runtime preflight receipt")
    parser.add_argument("--unit", default=DEFAULT_UNIT)
    parser.add_argument("--resident-source", default=DEFAULT_RESIDENT_SOURCE)
    parser.add_argument("--provider-source", default=DEFAULT_PROVIDER_SOURCE)
    parser.add_argument("--handoff-source", default=DEFAULT_HANDOFF_SOURCE)
    parser.add_argument("--socket-path")
    parser.add_argument("--package-state-file")
    args = parser.parse_args(argv)
    receipt = collect_preflight(
        unit=args.unit,
        resident_source=args.resident_source,
        provider_source=args.provider_source,
        handoff_source=args.handoff_source,
        socket_path=args.socket_path,
        package_state_file=args.package_state_file,
    )
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    return 0 if receipt["ready_state"] == READY else 4


if __name__ == "__main__":
    raise SystemExit(main())
