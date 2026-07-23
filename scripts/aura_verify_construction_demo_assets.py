#!/usr/bin/env python3
# ruff: noqa: E402
"""Fail-closed verification helpers for Construction demo build assets."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any, BinaryIO

from defusedxml import ElementTree as ET

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from aura_event_contracts import stable_digest

ASSET_VERIFIER_VERSION = "AURA_CONSTRUCTION_DEMO_ASSET_VERIFIER_V4"
MAX_COMMAND_OUTPUT_BYTES = 64 * 1024
MAX_GLB_BYTES = 512 * 1024 * 1024
MAX_SVG_BYTES = 32 * 1024 * 1024
GLB_MAGIC = b"glTF"
GLB_VERSION = 2
GLB_JSON_CHUNK = 0x4E4F534A
GLB_BIN_CHUNK = 0x004E4942
FORBIDDEN_SVG_RAW = (b"<!DOCTYPE", b"<!ENTITY")
_EXTERNAL_SCHEMES = ("http:", "https:", "//", "data:", "javascript:", "file:")
_CSS_URL = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.IGNORECASE | re.DOTALL)
_CSS_IMPORT = re.compile(r"@import\b", re.IGNORECASE)


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
    output_limit_exceeded: bool = False
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
            "stdout": self.stdout,
            "stderr": self.stderr,
            "stdout_truncated": self.stdout_truncated,
            "stderr_truncated": self.stderr_truncated,
            "timed_out": self.timed_out,
            "output_limit_exceeded": self.output_limit_exceeded,
        }

    def to_content_dict(self) -> dict[str, Any]:
        return {**self._body(), "receipt_digest": self.receipt_digest}

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.to_content_dict(),
            "duration_seconds": self.duration_seconds,
        }


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
    return value[:maximum_bytes].decode("utf-8", errors="replace"), truncated


def _terminate_process_group(process: subprocess.Popen[bytes]) -> None:
    if os.name == "nt":
        if process.poll() is not None:
            return
        try:
            process.terminate()
            process.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            process.kill()
        return

    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=0.5)
    except subprocess.TimeoutExpired:
        pass
    time.sleep(0.05)
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def _read_capped(
    stream: BinaryIO,
    buffer: bytearray,
    overflow: threading.Event,
    maximum_bytes: int,
) -> None:
    try:
        while chunk := stream.read(8192):
            remaining = maximum_bytes + 1 - len(buffer)
            if remaining > 0:
                buffer.extend(chunk[:remaining])
            if len(buffer) > maximum_bytes:
                overflow.set()
                return
    finally:
        stream.close()


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

    requested_executable = Path(command[0]).expanduser()
    if requested_executable.is_absolute():
        executable = requested_executable.resolve(strict=True)
    else:
        discovered = shutil.which(command[0], path=merged_env["PATH"])
        if not discovered:
            raise FileNotFoundError(f"command executable is unavailable: {command[0]}")
        executable = Path(discovered).resolve(strict=True)
    argv = [str(executable), *command[1:]]

    started = time.monotonic()
    process = subprocess.Popen(
        argv,
        cwd=workdir,
        env=merged_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=(os.name != "nt"),
        creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0),
    )
    assert process.stdout is not None and process.stderr is not None
    stdout_buffer = bytearray()
    stderr_buffer = bytearray()
    overflow = threading.Event()
    readers = (
        threading.Thread(
            target=_read_capped,
            args=(process.stdout, stdout_buffer, overflow, MAX_COMMAND_OUTPUT_BYTES),
            daemon=True,
        ),
        threading.Thread(
            target=_read_capped,
            args=(process.stderr, stderr_buffer, overflow, MAX_COMMAND_OUTPUT_BYTES),
            daemon=True,
        ),
    )
    for reader in readers:
        reader.start()

    timed_out = False
    output_limit_exceeded = False
    deadline = started + timeout_seconds
    while True:
        if overflow.is_set():
            output_limit_exceeded = True
            _terminate_process_group(process)
            break
        if time.monotonic() >= deadline:
            timed_out = True
            _terminate_process_group(process)
            break
        if process.poll() is not None:
            _terminate_process_group(process)
            break
        time.sleep(0.01)
    try:
        process.wait(timeout=1.0)
    except subprocess.TimeoutExpired:
        _terminate_process_group(process)
    for reader in readers:
        reader.join(timeout=1.0)
    if overflow.is_set():
        output_limit_exceeded = True
        _terminate_process_group(process)

    duration = round(time.monotonic() - started, 6)
    stdout, stdout_truncated = _bounded_text(bytes(stdout_buffer))
    stderr, stderr_truncated = _bounded_text(bytes(stderr_buffer))
    returncode = -1 if timed_out else (-2 if output_limit_exceeded else int(process.returncode or 0))
    receipt = CommandReceipt(
        command=tuple(argv),
        returncode=returncode,
        duration_seconds=duration,
        stdout=stdout,
        stderr=stderr,
        stdout_truncated=stdout_truncated or output_limit_exceeded,
        stderr_truncated=stderr_truncated or output_limit_exceeded,
        timed_out=timed_out,
        output_limit_exceeded=output_limit_exceeded,
    )
    if timed_out or output_limit_exceeded or receipt.returncode != 0:
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


def _parse_glb_chunks(data: bytes) -> tuple[dict[str, Any], int, bytes | None]:
    offset = 12
    chunk_index = 0
    document: dict[str, Any] | None = None
    binary_payload: bytes | None = None
    while offset < len(data):
        if len(data) - offset < 8:
            raise ValueError("GLB contains an incomplete trailing chunk header")
        chunk_length, chunk_type = struct.unpack_from("<II", data, offset)
        if chunk_length % 4 != 0:
            raise ValueError("GLB chunk length must be 4-byte aligned")
        payload_start = offset + 8
        payload_end = payload_start + chunk_length
        if payload_end < payload_start or payload_end > len(data):
            raise ValueError("GLB chunk range exceeds the declared file length")
        payload = data[payload_start:payload_end]
        if chunk_index == 0:
            if chunk_type != GLB_JSON_CHUNK or chunk_length <= 0:
                raise ValueError("GLB first chunk must be a non-empty JSON chunk")
            try:
                parsed = json.loads(payload.rstrip(b" \x00").decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError("GLB JSON chunk is not valid UTF-8 JSON") from exc
            if not isinstance(parsed, dict):
                raise ValueError("GLB JSON document must be an object")
            document = parsed
        elif chunk_index == 1 and chunk_type == GLB_BIN_CHUNK and binary_payload is None:
            binary_payload = payload
        elif chunk_type == GLB_JSON_CHUNK:
            raise ValueError("GLB must contain exactly one JSON chunk")
        else:
            raise ValueError("GLB contains an unsupported or duplicate chunk")
        offset = payload_end
        chunk_index += 1
    if offset != len(data) or document is None:
        raise ValueError("GLB chunk layout is incomplete")
    return document, chunk_index, binary_payload


def _validate_glb_embedded_layout(document: Mapping[str, Any], binary_payload: bytes | None) -> None:
    buffers = document.get("buffers", [])
    if not isinstance(buffers, list) or len(buffers) > 1:
        raise ValueError("GLB buffers must contain at most one embedded buffer")
    buffer_byte_length = 0
    if buffers:
        buffer = buffers[0]
        if not isinstance(buffer, Mapping) or "uri" in buffer:
            raise ValueError("GLB must not reference external or data URI resources")
        buffer_byte_length = buffer.get("byteLength")
        if type(buffer_byte_length) is not int or buffer_byte_length <= 0:
            raise ValueError("GLB embedded buffer byteLength is invalid")
        if (
            binary_payload is None
            or len(binary_payload) < buffer_byte_length
            or len(binary_payload) > buffer_byte_length + 3
        ):
            raise ValueError("GLB BIN chunk does not match the declared embedded buffer")
    elif binary_payload is not None:
        raise ValueError("GLB BIN chunk is present without a declared embedded buffer")

    buffer_views = document.get("bufferViews", [])
    if not isinstance(buffer_views, list):
        raise ValueError("GLB bufferViews must be an array")
    validated_views: list[tuple[int, int, int | None]] = []
    for view in buffer_views:
        if not isinstance(view, Mapping) or view.get("buffer") != 0 or not buffers:
            raise ValueError("GLB bufferView references an invalid embedded buffer")
        byte_offset = view.get("byteOffset", 0)
        byte_length = view.get("byteLength")
        byte_stride = view.get("byteStride")
        if (
            type(byte_offset) is not int
            or byte_offset < 0
            or type(byte_length) is not int
            or byte_length <= 0
            or byte_offset + byte_length > buffer_byte_length
            or (
                byte_stride is not None
                and (type(byte_stride) is not int or byte_stride < 4 or byte_stride > 252 or byte_stride % 4 != 0)
            )
        ):
            raise ValueError("GLB bufferView range or stride is invalid")
        validated_views.append((byte_offset, byte_length, byte_stride))

    component_bytes = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}
    type_components = {
        "SCALAR": 1,
        "VEC2": 2,
        "VEC3": 3,
        "VEC4": 4,
        "MAT2": 4,
        "MAT3": 9,
        "MAT4": 16,
    }
    accessors = document.get("accessors", [])
    if not isinstance(accessors, list):
        raise ValueError("GLB accessors must be an array")
    accessor_metadata: list[tuple[int, int, int, int, int]] = []
    for accessor in accessors:
        if not isinstance(accessor, Mapping) or "sparse" in accessor:
            raise ValueError("GLB accessor is invalid or uses unsupported sparse storage")
        view_index = accessor.get("bufferView")
        component_type = accessor.get("componentType")
        accessor_type = accessor.get("type")
        count = accessor.get("count")
        byte_offset = accessor.get("byteOffset", 0)
        if (
            type(view_index) is not int
            or view_index < 0
            or view_index >= len(validated_views)
            or component_type not in component_bytes
            or accessor_type not in type_components
            or type(count) is not int
            or count <= 0
            or type(byte_offset) is not int
            or byte_offset < 0
        ):
            raise ValueError("GLB accessor metadata is invalid")
        component_size = component_bytes[component_type]
        element_size = component_size * type_components[accessor_type]
        view_offset, view_length, byte_stride = validated_views[view_index]
        stride = byte_stride or element_size
        required = byte_offset + (count - 1) * stride + element_size
        if (
            byte_offset % component_size != 0
            or stride < element_size
            or stride % component_size != 0
            or required > view_length
        ):
            raise ValueError("GLB accessor range exceeds its bufferView")
        accessor_metadata.append((view_offset + byte_offset, count, stride, component_type, element_size))

    images = document.get("images", [])
    if not isinstance(images, list):
        raise ValueError("GLB images must be an array")
    for image in images:
        if not isinstance(image, Mapping) or "uri" in image:
            raise ValueError("GLB must not reference external or data URI resources")
        view_index = image.get("bufferView")
        if type(view_index) is not int or view_index < 0 or view_index >= len(validated_views):
            raise ValueError("GLB embedded image bufferView is invalid")
        if type(image.get("mimeType")) is not str or not image.get("mimeType"):
            raise ValueError("GLB embedded image mimeType is invalid")

    meshes = document.get("meshes", [])
    if not isinstance(meshes, list):
        raise ValueError("GLB meshes must be an array")
    for mesh in meshes:
        primitives = mesh.get("primitives") if isinstance(mesh, Mapping) else None
        if not isinstance(primitives, list) or not primitives:
            raise ValueError("GLB mesh primitives are invalid")
        for primitive in primitives:
            if not isinstance(primitive, Mapping):
                raise ValueError("GLB mesh primitive must be an object")
            attributes = primitive.get("attributes")
            if not isinstance(attributes, Mapping) or not attributes:
                raise ValueError("GLB mesh primitive attributes are invalid")
            for accessor_index in attributes.values():
                if type(accessor_index) is not int or accessor_index < 0 or accessor_index >= len(accessors):
                    raise ValueError("GLB mesh attribute accessor index is invalid")
            position_index = attributes.get("POSITION")
            if type(position_index) is not int or position_index < 0 or position_index >= len(accessors):
                raise ValueError("GLB mesh primitive lacks a valid POSITION accessor")
            if "indices" in primitive:
                accessor_index = primitive["indices"]
                if type(accessor_index) is not int or accessor_index < 0 or accessor_index >= len(accessors):
                    raise ValueError("GLB mesh index accessor is invalid")
                index_accessor = accessors[accessor_index]
                if index_accessor.get("type") != "SCALAR" or index_accessor.get("componentType") not in {
                    5121,
                    5123,
                    5125,
                }:
                    raise ValueError("GLB mesh index accessor type is invalid")
                if binary_payload is None:
                    raise ValueError("GLB mesh indices require an embedded BIN chunk")
                absolute_offset, count, stride, component_type, element_size = accessor_metadata[accessor_index]
                format_by_component = {5121: "<B", 5123: "<H", 5125: "<I"}
                if element_size not in {1, 2, 4}:
                    raise ValueError("GLB mesh index accessor width is invalid")
                max_index = max(
                    struct.unpack_from(
                        format_by_component[component_type], binary_payload, absolute_offset + i * stride
                    )[0]
                    for i in range(count)
                )
                position_count = accessors[position_index].get("count")
                if type(position_count) is not int or max_index >= position_count:
                    raise ValueError("GLB mesh index value exceeds the POSITION accessor range")

    nodes = document.get("nodes", [])
    if not isinstance(nodes, list):
        raise ValueError("GLB nodes must be an array")
    for node in nodes:
        if not isinstance(node, Mapping):
            raise ValueError("GLB node must be an object")
        if "mesh" in node and (type(node["mesh"]) is not int or node["mesh"] < 0 or node["mesh"] >= len(meshes)):
            raise ValueError("GLB node mesh index is invalid")
        children = node.get("children", [])
        if not isinstance(children, list) or any(
            type(child) is not int or child < 0 or child >= len(nodes) for child in children
        ):
            raise ValueError("GLB node child index is invalid")

    scenes = document.get("scenes", [])
    if not isinstance(scenes, list):
        raise ValueError("GLB scenes must be an array")
    for scene in scenes:
        scene_nodes = scene.get("nodes", []) if isinstance(scene, Mapping) else None
        if not isinstance(scene_nodes, list) or any(
            type(node) is not int or node < 0 or node >= len(nodes) for node in scene_nodes
        ):
            raise ValueError("GLB scene node index is invalid")
    if "scene" in document and (
        type(document["scene"]) is not int or document["scene"] < 0 or document["scene"] >= len(scenes)
    ):
        raise ValueError("GLB default scene index is invalid")


def verify_glb(path: Path, *, root: Path) -> dict[str, Any]:
    asset = require_local_regular_file(path, root=root, maximum_bytes=MAX_GLB_BYTES)
    data = asset.read_bytes()
    if len(data) < 20:
        raise ValueError("GLB is shorter than its required header and JSON chunk")
    magic, version, declared_length = struct.unpack_from("<4sII", data, 0)
    if magic != GLB_MAGIC or version != GLB_VERSION or declared_length != len(data):
        raise ValueError("GLB header, version, or declared length is invalid")
    document, chunk_count, binary_payload = _parse_glb_chunks(data)
    asset_metadata = document.get("asset")
    if not isinstance(asset_metadata, dict):
        raise ValueError("GLB JSON must contain glTF asset metadata")
    asset_version = asset_metadata.get("version")
    if type(asset_version) is not str or asset_version.split(".", 1)[0] != "2":
        raise ValueError("GLB glTF asset.version must be compatible with version 2")
    _walk_numbers(document)
    _validate_glb_embedded_layout(document, binary_payload)
    payload = {
        "version": ASSET_VERIFIER_VERSION,
        "kind": "GLB",
        "path": asset.relative_to(root.resolve(strict=True)).as_posix(),
        "byte_length": len(data),
        "sha256": sha256_file(asset),
        "glb_version": version,
        "gltf_asset_version": asset_version,
        "chunk_count": chunk_count,
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


def _validate_resource_reference(value: str) -> None:
    candidate = value.strip()
    if len(candidate) < 2 or not candidate.startswith("#"):
        raise ValueError("SVG contains an external or executable reference")


def _validate_css(css: str) -> None:
    if "\\" in css:
        raise ValueError("SVG contains an external or executable reference")
    if _CSS_IMPORT.search(css):
        raise ValueError("SVG contains an external or executable reference")
    for match in _CSS_URL.finditer(css):
        _validate_resource_reference(match.group(2))


def _secure_atomic_write(path: Path, payload: bytes, *, root: Path) -> None:
    root_resolved = root.expanduser().resolve(strict=True)
    candidate = path.expanduser()
    if not candidate.is_absolute():
        candidate = root_resolved / candidate
    candidate.parent.mkdir(parents=True, exist_ok=True)
    parent = candidate.parent.resolve(strict=True)
    try:
        parent.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError("atomic write target escapes its allowed root") from exc
    target = parent / candidate.name
    if target.exists() and target.is_symlink():
        raise ValueError("atomic write target must not be a symlink")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        try:
            directory_fd = os.open(parent, os.O_RDONLY)
        except OSError:
            directory_fd = -1
        if directory_fd >= 0:
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)


def sanitize_svg(path: Path, *, root: Path) -> dict[str, Any]:
    asset = require_local_regular_file(path, root=root, maximum_bytes=MAX_SVG_BYTES)
    raw = asset.read_bytes()
    upper = raw.upper()
    if any(marker in upper for marker in FORBIDDEN_SVG_RAW):
        raise ValueError("SVG contains a forbidden document type or entity declaration")
    try:
        root_element = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise ValueError("SVG is not well-formed XML") from exc
    for element in root_element.iter():
        local_tag = element.tag.rsplit("}", 1)[-1].lower()
        if local_tag in {"script", "foreignobject"}:
            raise ValueError("SVG contains executable or foreign content")
        if local_tag == "style":
            _validate_css(element.text or "")
        for name, value in element.attrib.items():
            local_name = name.rsplit("}", 1)[-1].lower()
            if local_name.startswith("on"):
                raise ValueError("SVG contains an event handler")
            if local_name in {"href", "src"}:
                _validate_resource_reference(value)
            if local_name == "style":
                _validate_css(value)
    _canonicalize_xml(root_element)
    serialized = ET.tostring(root_element, encoding="utf-8", xml_declaration=True)
    if not serialized or len(serialized) > MAX_SVG_BYTES:
        raise ValueError("sanitized SVG violates its byte budget")
    _secure_atomic_write(asset, serialized, root=root)
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


def atomic_json(path: Path, value: Mapping[str, Any], *, root: Path) -> None:
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")
    _secure_atomic_write(path, payload, root=root)
