#!/usr/bin/env python3
"""Fail-closed verification helpers for Construction demo build assets."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
import time
from typing import Any, Mapping, Sequence
import xml.etree.ElementTree as ET

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from aura_event_contracts import stable_digest

ASSET_VERIFIER_VERSION = "AURA_CONSTRUCTION_DEMO_ASSET_VERIFIER_V1"
MAX_COMMAND_OUTPUT_BYTES = 64 * 1024
MAX_GLB_BYTES = 512 * 1024 * 1024
MAX_SVG_BYTES = 32 * 1024 * 1024
GLB_MAGIC = b"glTF"
GLB_VERSION = 2
GLB_JSON_CHUNK = 0x4E4F534A
FORBIDDEN_SVG_RAW = (b"<!DOCTYPE", b"<!ENTITY")


@dataclass(frozen=True)
class CommandReceipt:
    command: tuple[str, ...]
    returncode: int
    duration_seconds: float
    stdout: str
    stderr: str
    stdout_truncated: bool
    stderr_truncated: bool
    timed_out: bool
    receipt_digest: str = ""

    def __post_init__(self) -> None:
        payload = self._body()
        digest = stable_digest(payload)
        if self.receipt_digest and self.receipt_digest != digest:
            raise ValueError("receipt_digest does not match command receipt")
        object.__setattr__(self, "receipt_digest", digest)

    def _body(self) -> dict[str, Any]:
        return {
            "version": ASSET_VERIFIER_VERSION,
            "command": list(self.command),
            "returncode": self.returncode,
            "duration_seconds": self.duration_seconds,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "stdout_truncated": self.stdout_truncated,
            "stderr_truncated": self.stderr_truncated,
            "timed_out": self.timed_out,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._body(), "receipt_digest": self.receipt_digest}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def require_local_regular_file(
    path: Path,
    *,
    root: Path,
    maximum_bytes: int,
    allow_empty: bool = False,
) -> Path:
    root_resolved = root.expanduser().resolve(strict=True)
    candidate = path.expanduser()
    if not candidate.is_absolute():
        candidate = root_resolved / candidate
    if candidate.is_symlink():
        raise ValueError("asset path must not be a symlink")
    candidate = candidate.resolve(strict=True)
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError("asset path escapes repository root") from exc
    if not candidate.is_file() or candidate.is_symlink():
        raise ValueError("asset path must be a regular non-symlink file")
    size = candidate.stat().st_size
    if (not allow_empty and size == 0) or size > maximum_bytes:
        raise ValueError("asset file violates its byte budget")
    return candidate


def _bounded_text(value: bytes, maximum_bytes: int = MAX_COMMAND_OUTPUT_BYTES) -> tuple[str, bool]:
    truncated = len(value) > maximum_bytes
    body = value[:maximum_bytes]
    return body.decode("utf-8", errors="replace"), truncated


def run_bounded_command(
    command: Sequence[str],
    *,
    cwd: Path,
    timeout_seconds: float,
    env: Mapping[str, str] | None = None,
) -> CommandReceipt:
    if not command or any(type(item) is not str or not item for item in command):
        raise ValueError("command must contain non-empty string arguments")
    if timeout_seconds <= 0 or timeout_seconds > 1800:
        raise ValueError("timeout_seconds must be in (0, 1800]")
    workdir = cwd.expanduser().resolve(strict=True)
    merged_env = {
        "PATH": os.environ.get("PATH", ""),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONHASHSEED": "0",
    }
    if env:
        for key, value in env.items():
            if type(key) is not str or type(value) is not str or "\x00" in key + value:
                raise ValueError("command environment must contain bounded strings")
            merged_env[key] = value
    started = time.monotonic()
    try:
        completed = subprocess.run(
            list(command),
            cwd=workdir,
            env=merged_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout_seconds,
        )
        duration = round(time.monotonic() - started, 6)
        stdout, stdout_truncated = _bounded_text(completed.stdout)
        stderr, stderr_truncated = _bounded_text(completed.stderr)
        receipt = CommandReceipt(
            command=tuple(command),
            returncode=completed.returncode,
            duration_seconds=duration,
            stdout=stdout,
            stderr=stderr,
            stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated,
            timed_out=False,
        )
    except subprocess.TimeoutExpired as exc:
        duration = round(time.monotonic() - started, 6)
        stdout, stdout_truncated = _bounded_text(exc.stdout or b"")
        stderr, stderr_truncated = _bounded_text(exc.stderr or b"")
        receipt = CommandReceipt(
            command=tuple(command),
            returncode=-1,
            duration_seconds=duration,
            stdout=stdout,
            stderr=stderr,
            stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated,
            timed_out=True,
        )
        raise RuntimeError(json.dumps(receipt.to_dict(), sort_keys=True)) from exc
    if receipt.returncode != 0:
        raise RuntimeError(json.dumps(receipt.to_dict(), sort_keys=True))
    return receipt


def _walk_numbers(value: Any) -> None:
    if type(value) is float and not math.isfinite(value):
        raise ValueError("GLB JSON contains a non-finite number")
    if isinstance(value, list):
        for item in value:
            _walk_numbers(item)
    elif isinstance(value, dict):
        for item in value.values():
            _walk_numbers(item)


def verify_glb(path: Path, *, root: Path) -> dict[str, Any]:
    asset = require_local_regular_file(path, root=root, maximum_bytes=MAX_GLB_BYTES)
    data = asset.read_bytes()
    if len(data) < 20:
        raise ValueError("GLB is shorter than its required header and JSON chunk")
    magic, version, declared_length = struct.unpack_from("<4sII", data, 0)
    if magic != GLB_MAGIC or version != GLB_VERSION or declared_length != len(data):
        raise ValueError("GLB header, version, or declared length is invalid")
    json_length, json_type = struct.unpack_from("<II", data, 12)
    if json_type != GLB_JSON_CHUNK or json_length <= 0 or 20 + json_length > len(data):
        raise ValueError("GLB JSON chunk is invalid")
    try:
        document = json.loads(data[20 : 20 + json_length].rstrip(b" \x00").decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("GLB JSON chunk is not valid UTF-8 JSON") from exc
    if not isinstance(document, dict):
        raise ValueError("GLB JSON document must be an object")
    _walk_numbers(document)
    for collection in ("buffers", "images"):
        for item in document.get(collection, ()):
            if isinstance(item, dict) and "uri" in item:
                raise ValueError("GLB must not reference external or data URI resources")
    payload = {
        "version": ASSET_VERIFIER_VERSION,
        "kind": "GLB",
        "path": asset.relative_to(root.resolve(strict=True)).as_posix(),
        "byte_length": len(data),
        "sha256": sha256_file(asset),
        "glb_version": version,
        "scene_count": len(document.get("scenes", ())),
        "node_count": len(document.get("nodes", ())),
        "mesh_count": len(document.get("meshes", ())),
        "external_resource_fetch": False,
        "survey_authority": False,
    }
    return {**payload, "verification_digest": stable_digest(payload)}


def _canonicalize_xml(element: ET.Element) -> None:
    sorted_attributes = sorted(element.attrib.items())
    element.attrib.clear()
    element.attrib.update(sorted_attributes)
    if element.text is not None and not element.text.strip():
        element.text = None
    if element.tail is not None and not element.tail.strip():
        element.tail = None
    for child in list(element):
        _canonicalize_xml(child)


def sanitize_svg(path: Path, *, root: Path) -> dict[str, Any]:
    asset = require_local_regular_file(path, root=root, maximum_bytes=MAX_SVG_BYTES)
    raw = asset.read_bytes()
    upper = raw.upper()
    if any(marker in upper for marker in FORBIDDEN_SVG_RAW):
        raise ValueError("SVG contains a forbidden document type or entity declaration")
    try:
        tree = ET.parse(asset)
    except ET.ParseError as exc:
        raise ValueError("SVG is not well-formed XML") from exc
    root_element = tree.getroot()
    for element in root_element.iter():
        local_tag = element.tag.rsplit("}", 1)[-1].lower()
        if local_tag in {"script", "foreignobject"}:
            raise ValueError("SVG contains executable or foreign content")
        for name, value in element.attrib.items():
            local_name = name.rsplit("}", 1)[-1].lower()
            if local_name.startswith("on"):
                raise ValueError("SVG contains an event handler")
            if local_name in {"href", "src"}:
                lowered = value.strip().lower()
                if lowered.startswith(("http:", "https:", "//", "data:", "javascript:", "file:")):
                    raise ValueError("SVG contains an external or executable reference")
    _canonicalize_xml(root_element)
    temporary = asset.with_suffix(asset.suffix + ".sanitized.tmp")
    tree.write(temporary, encoding="utf-8", xml_declaration=True)
    if temporary.stat().st_size == 0 or temporary.stat().st_size > MAX_SVG_BYTES:
        temporary.unlink(missing_ok=True)
        raise ValueError("sanitized SVG violates its byte budget")
    temporary.replace(asset)
    payload = {
        "version": ASSET_VERIFIER_VERSION,
        "kind": "SVG",
        "path": asset.relative_to(root.resolve(strict=True)).as_posix(),
        "byte_length": asset.stat().st_size,
        "sha256": sha256_file(asset),
        "script_present": False,
        "external_reference_present": False,
        "survey_authority": False,
    }
    return {**payload, "verification_digest": stable_digest(payload)}


def atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)
