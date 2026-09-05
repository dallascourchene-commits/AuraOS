"""Fail-closed AirLLM loading membrane.

Security contract:
- model bytes must be local and match an exact SHA-256 allowlist;
- model artifacts must use structurally valid Safetensors weights;
- pickle-family weights and executable model payloads are rejected;
- the AirLLM loader source file must match an exact SHA-256 allowlist;
- every guarded Transformers loader boundary receives ``trust_remote_code=False``;
- dynamic-module loading is denied while the membrane is active;
- model and loader identities are revalidated immediately before invocation;
- destructive ``delete_original=True`` requests are rejected.

The wrapper does not make untrusted/custom code safe. Models that require remote
Python code or unsafe serialization fail closed instead of being opted in.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from hashlib import sha256
import hmac
import inspect
import json
import os
from pathlib import Path
import re
import stat
import struct
import threading
from types import ModuleType
from typing import Any, Iterable, Mapping, Protocol

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_DIRECTORY_DIGEST_SCHEMA = "AURA-MODEL-DIR-SHA256-v2"
_SAFETENSORS_HEADER_LIMIT = 64 * 1024 * 1024
_UNSAFE_WEIGHT_SUFFIXES = frozenset({
    ".bin", ".pt", ".pth", ".ckpt", ".pkl", ".pickle", ".joblib",
})
_EXECUTABLE_SUFFIXES = frozenset({
    ".py", ".pyc", ".pyo", ".so", ".dll", ".dylib", ".pyd",
    ".sh", ".bash", ".zsh", ".ps1", ".bat", ".cmd", ".exe", ".com", ".msi",
})
_REMOTE_CODE_BOUNDARIES = (
    ("AutoConfig", "from_pretrained"),
    ("AutoTokenizer", "from_pretrained"),
    ("AutoModel", "from_pretrained"),
    ("AutoModelForCausalLM", "from_pretrained"),
    ("AutoModelForCausalLM", "from_config"),
)
_REMOTE_CODE_GUARD_LOCK = threading.RLock()


class AirLLMSecurityError(RuntimeError):
    """Base class for fail-closed AirLLM admission failures."""


class InvalidAllowlistError(AirLLMSecurityError):
    """Raised when an allowlist is malformed or ambiguous."""


class ModelIntegrityError(AirLLMSecurityError):
    """Raised when local model identity cannot be established exactly."""


class UnsafeModelArtifactError(ModelIntegrityError):
    """Raised when a model tree contains unsafe or malformed artifacts."""


class LoaderSourceIntegrityError(AirLLMSecurityError):
    """Raised when the executing AirLLM loader source is not exactly pinned."""


class RemoteCodeTrustError(AirLLMSecurityError):
    """Raised when remote-code execution is requested or observed."""


class UnsafeLoadOptionError(AirLLMSecurityError):
    """Raised for destructive or authority-widening load options."""


class _AirLLMLoader(Protocol):
    @classmethod
    def from_pretrained(cls, pretrained_model_name_or_path: str, *args: Any, **kwargs: Any) -> Any: ...


@dataclass(frozen=True)
class VerifiedModel:
    model_id: str
    path: str
    sha256: str
    kind: str


@dataclass(frozen=True)
class VerifiedLoaderSource:
    path: str
    sha256: str


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _validate_digest(value: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise InvalidAllowlistError("SHA-256 values must be exact lowercase 64-hex strings")
    return value


def _normalize_digest_set(values: Iterable[str] | None, *, label: str) -> frozenset[str]:
    if values is None or isinstance(values, (str, bytes)):
        raise InvalidAllowlistError(f"{label} must be a non-empty collection of SHA-256 values")
    try:
        normalized = frozenset(_validate_digest(value) for value in values)
    except TypeError as exc:
        raise InvalidAllowlistError(f"{label} must be an iterable of SHA-256 values") from exc
    if not normalized:
        raise InvalidAllowlistError(f"{label} must not be empty")
    return normalized


def normalize_allowlist(allowlist: Mapping[str, Iterable[str]]) -> dict[str, frozenset[str]]:
    """Copy and strictly validate a model-id -> exact SHA-256 allowlist mapping."""
    if not isinstance(allowlist, Mapping) or not allowlist:
        raise InvalidAllowlistError("model allowlist must be a non-empty mapping")
    normalized: dict[str, frozenset[str]] = {}
    for model_id, digests in allowlist.items():
        if not isinstance(model_id, str) or not model_id or model_id.strip() != model_id:
            raise InvalidAllowlistError("model ids must be non-empty exact strings")
        normalized[model_id] = _normalize_digest_set(
            digests, label=f"model {model_id!r} digest allowlist"
        )
    return normalized


def _assert_regular_local_file(path: Path) -> os.stat_result:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise ModelIntegrityError(f"artifact is not readable: {path}") from exc
    if stat.S_ISLNK(metadata.st_mode):
        raise ModelIntegrityError(f"symbolic links are not admitted: {path}")
    if not stat.S_ISREG(metadata.st_mode):
        raise ModelIntegrityError(f"artifact must be a regular file: {path}")
    return metadata


def _sha256_regular_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    before = _assert_regular_local_file(path)
    digest = sha256()
    try:
        with path.open("rb", buffering=0) as handle:
            opened = os.fstat(handle.fileno())
            if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
                raise ModelIntegrityError(f"artifact changed before hashing: {path}")
            while True:
                chunk = handle.read(chunk_size)
                if not chunk:
                    break
                digest.update(chunk)
            after_open = os.fstat(handle.fileno())
    except ModelIntegrityError:
        raise
    except OSError as exc:
        raise ModelIntegrityError(f"failed while hashing artifact: {path}") from exc
    try:
        after_path = path.lstat()
    except OSError as exc:
        raise ModelIntegrityError(f"artifact disappeared after hashing: {path}") from exc
    identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    identity_opened = (after_open.st_dev, after_open.st_ino, after_open.st_size, after_open.st_mtime_ns)
    identity_after = (after_path.st_dev, after_path.st_ino, after_path.st_size, after_path.st_mtime_ns)
    if identity_before != identity_opened or identity_before != identity_after:
        raise ModelIntegrityError(f"artifact changed while hashing: {path}")
    return digest.hexdigest()


def _validate_safetensors_file(path: Path) -> None:
    """Validate enough of the Safetensors container to reject renamed/random payloads.

    This is a structural admission gate, not a substitute for the Safetensors parser.
    It validates the 8-byte little-endian header length, JSON header shape, tensor
    descriptors, and non-overlapping in-bounds data ranges without deserializing code.
    """
    metadata = _assert_regular_local_file(path)
    if metadata.st_size < 10:
        raise UnsafeModelArtifactError(f"Safetensors file is too small: {path}")
    try:
        with path.open("rb", buffering=0) as handle:
            raw_length = handle.read(8)
            if len(raw_length) != 8:
                raise UnsafeModelArtifactError(f"Safetensors header length is truncated: {path}")
            (header_len,) = struct.unpack("<Q", raw_length)
            if header_len <= 1 or header_len > _SAFETENSORS_HEADER_LIMIT:
                raise UnsafeModelArtifactError(f"Safetensors header length is invalid: {path}")
            if 8 + header_len > metadata.st_size:
                raise UnsafeModelArtifactError(f"Safetensors header exceeds file bounds: {path}")
            header_bytes = handle.read(header_len)
    except UnsafeModelArtifactError:
        raise
    except OSError as exc:
        raise UnsafeModelArtifactError(f"could not inspect Safetensors file: {path}") from exc
    try:
        header_text = header_bytes.decode("utf-8").rstrip(" ")
        header = json.loads(header_text)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UnsafeModelArtifactError(f"Safetensors header is not valid UTF-8 JSON: {path}") from exc
    if not isinstance(header, dict):
        raise UnsafeModelArtifactError(f"Safetensors header must be a JSON object: {path}")

    data_len = metadata.st_size - 8 - header_len
    ranges: list[tuple[int, int]] = []
    tensor_count = 0
    for name, descriptor in header.items():
        if name == "__metadata__":
            if not isinstance(descriptor, dict):
                raise UnsafeModelArtifactError(f"Safetensors metadata must be an object: {path}")
            continue
        tensor_count += 1
        if not isinstance(name, str) or not name or not isinstance(descriptor, dict):
            raise UnsafeModelArtifactError(f"Safetensors tensor descriptor is malformed: {path}")
        dtype = descriptor.get("dtype")
        shape = descriptor.get("shape")
        offsets = descriptor.get("data_offsets")
        if not isinstance(dtype, str) or not dtype:
            raise UnsafeModelArtifactError(f"Safetensors tensor dtype is malformed: {path}")
        if not isinstance(shape, list) or any(
            not isinstance(dim, int) or isinstance(dim, bool) or dim < 0 for dim in shape
        ):
            raise UnsafeModelArtifactError(f"Safetensors tensor shape is malformed: {path}")
        if (
            not isinstance(offsets, list)
            or len(offsets) != 2
            or any(not isinstance(x, int) or isinstance(x, bool) for x in offsets)
        ):
            raise UnsafeModelArtifactError(f"Safetensors tensor offsets are malformed: {path}")
        start, end = offsets
        if start < 0 or end < start or end > data_len:
            raise UnsafeModelArtifactError(f"Safetensors tensor offsets are out of bounds: {path}")
        ranges.append((start, end))
    if tensor_count == 0:
        raise UnsafeModelArtifactError(f"Safetensors file contains no tensor descriptors: {path}")
    previous_end = 0
    for start, end in sorted(ranges):
        if start < previous_end:
            raise UnsafeModelArtifactError(f"Safetensors tensor ranges overlap: {path}")
        previous_end = max(previous_end, end)


def _assert_safe_model_artifacts(path: Path) -> None:
    if path.is_file():
        if path.suffix.lower() != ".safetensors":
            raise UnsafeModelArtifactError("single-file models must use .safetensors")
        _validate_safetensors_file(path)
        return

    safetensors_count = 0
    try:
        candidates = sorted(path.rglob("*"), key=lambda item: item.relative_to(path).as_posix())
    except OSError as exc:
        raise ModelIntegrityError(f"could not enumerate model directory: {path}") from exc
    for candidate in candidates:
        try:
            metadata = candidate.lstat()
        except OSError as exc:
            raise ModelIntegrityError(f"model directory changed during enumeration: {candidate}") from exc
        if stat.S_ISLNK(metadata.st_mode):
            raise ModelIntegrityError(f"symbolic links are not admitted: {candidate}")
        if stat.S_ISDIR(metadata.st_mode):
            continue
        if not stat.S_ISREG(metadata.st_mode):
            raise ModelIntegrityError(f"special files are not admitted: {candidate}")
        suffix = candidate.suffix.lower()
        if suffix in _UNSAFE_WEIGHT_SUFFIXES:
            raise UnsafeModelArtifactError(f"pickle-family model artifact is not admitted: {candidate}")
        if suffix in _EXECUTABLE_SUFFIXES:
            raise UnsafeModelArtifactError(f"executable model payload is not admitted: {candidate}")
        if suffix == ".safetensors":
            _validate_safetensors_file(candidate)
            safetensors_count += 1
    if safetensors_count == 0:
        raise UnsafeModelArtifactError("model directories must contain at least one valid .safetensors weight file")


def sha256_model_path(model_path: str | os.PathLike[str]) -> tuple[str, str]:
    """Return (digest, kind) for a safe local model file or canonical directory manifest."""
    path = Path(model_path).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve(strict=False)
    try:
        root_meta = path.lstat()
    except OSError as exc:
        raise ModelIntegrityError(f"model path does not exist: {path}") from exc
    if stat.S_ISLNK(root_meta.st_mode):
        raise ModelIntegrityError(f"symbolic model roots are not admitted: {path}")
    if stat.S_ISREG(root_meta.st_mode):
        _assert_safe_model_artifacts(path)
        return _sha256_regular_file(path), "file"
    if not stat.S_ISDIR(root_meta.st_mode):
        raise ModelIntegrityError(f"model path must be a regular file or directory: {path}")

    _assert_safe_model_artifacts(path)
    files: list[dict[str, Any]] = []
    candidates = sorted(path.rglob("*"), key=lambda item: item.relative_to(path).as_posix())
    for candidate in candidates:
        metadata = candidate.lstat()
        if stat.S_ISDIR(metadata.st_mode):
            continue
        relative = candidate.relative_to(path).as_posix()
        if relative.startswith("../") or relative == "..":
            raise ModelIntegrityError("model directory traversal detected")
        file_digest = _sha256_regular_file(candidate)
        files.append({"path": relative, "size": metadata.st_size, "sha256": file_digest})
    manifest = {"schema": _DIRECTORY_DIGEST_SCHEMA, "files": files}
    return sha256(_canonical_json(manifest)).hexdigest(), "directory"


def verify_model_allowlist(
    model_id: str,
    model_path: str | os.PathLike[str],
    allowlist: Mapping[str, Iterable[str]],
) -> VerifiedModel:
    exact = normalize_allowlist(allowlist)
    if model_id not in exact:
        raise ModelIntegrityError(f"model id is not allowlisted: {model_id!r}")
    digest, kind = sha256_model_path(model_path)
    if not any(hmac.compare_digest(digest, allowed) for allowed in exact[model_id]):
        raise ModelIntegrityError(f"SHA-256 mismatch for allowlisted model {model_id!r}")
    path = Path(model_path).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve(strict=False)
    return VerifiedModel(model_id=model_id, path=str(path), sha256=digest, kind=kind)


def sha256_loader_source(loader: Any) -> VerifiedLoaderSource:
    """Hash the exact source file that defines the selected AirLLM loader."""
    try:
        source = inspect.getsourcefile(loader) or inspect.getfile(loader)
    except (TypeError, OSError) as exc:
        raise LoaderSourceIntegrityError("AirLLM loader source cannot be resolved") from exc
    if not source:
        raise LoaderSourceIntegrityError("AirLLM loader source cannot be resolved")
    path = Path(source)
    try:
        digest = _sha256_regular_file(path)
    except ModelIntegrityError as exc:
        raise LoaderSourceIntegrityError(str(exc)) from exc
    return VerifiedLoaderSource(path=str(path.resolve()), sha256=digest)


def verify_loader_source(loader: Any, allowlist: Iterable[str] | None) -> VerifiedLoaderSource:
    allowed = _normalize_digest_set(allowlist, label="AirLLM loader source allowlist")
    verified = sha256_loader_source(loader)
    if not any(hmac.compare_digest(verified.sha256, digest) for digest in allowed):
        raise LoaderSourceIntegrityError("AirLLM loader source SHA-256 is not allowlisted")
    return verified


def _resolve_transformers_module(transformers_module: ModuleType | Any | None) -> Any:
    if transformers_module is not None:
        return transformers_module
    try:
        import transformers  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RemoteCodeTrustError("transformers is required for the AirLLM remote-code membrane") from exc
    return transformers


def _trust_argument_value(original: Any, args: tuple[Any, ...], kwargs: dict[str, Any]) -> tuple[bool, Any]:
    if "trust_remote_code" in kwargs:
        return True, kwargs["trust_remote_code"]
    try:
        signature = inspect.signature(original)
        bound = signature.bind_partial(*args, **kwargs)
    except (TypeError, ValueError):
        return False, None
    if "trust_remote_code" in bound.arguments:
        return True, bound.arguments["trust_remote_code"]
    return False, None


@contextmanager
def hard_false_remote_code_membrane(transformers_module: ModuleType | Any | None = None):
    """Force known Transformers model-loading boundaries to hard-false.

    Guarded loads are serialized because the patch is process-global. In addition to
    injecting ``trust_remote_code=False``, the membrane denies the dynamic-module
    resolver when it is exposed by the Transformers module.
    """
    module = _resolve_transformers_module(transformers_module)
    patches: list[tuple[Any, str, Any]] = []
    function_patches: list[tuple[Any, str, Any]] = []
    with _REMOTE_CODE_GUARD_LOCK:
        try:
            for class_name, method_name in _REMOTE_CODE_BOUNDARIES:
                cls = getattr(module, class_name, None)
                if cls is None or not hasattr(cls, method_name):
                    continue
                raw_descriptor = inspect.getattr_static(cls, method_name)
                original = getattr(cls, method_name)

                def guarded(*args: Any, __original: Any = original, __boundary: str = f"{class_name}.{method_name}", **kwargs: Any) -> Any:
                    present, value = _trust_argument_value(__original, args, kwargs)
                    if present and value is not False:
                        raise RemoteCodeTrustError(
                            f"{__boundary} attempted trust_remote_code={value!r}; only literal False is admitted"
                        )
                    if not present:
                        kwargs["trust_remote_code"] = False
                    return __original(*args, **kwargs)

                setattr(cls, method_name, staticmethod(guarded))
                patches.append((cls, method_name, raw_descriptor))

            dynamic_module = getattr(module, "dynamic_module_utils", None)
            if dynamic_module is not None and hasattr(dynamic_module, "get_class_from_dynamic_module"):
                original_dynamic = getattr(dynamic_module, "get_class_from_dynamic_module")

                def deny_dynamic_module(*args: Any, **kwargs: Any) -> Any:
                    raise RemoteCodeTrustError("dynamic Transformers module loading is not admitted")

                setattr(dynamic_module, "get_class_from_dynamic_module", deny_dynamic_module)
                function_patches.append((dynamic_module, "get_class_from_dynamic_module", original_dynamic))

            if not patches:
                raise RemoteCodeTrustError("no supported Transformers loader boundaries were found")
            yield
        finally:
            for obj, name, original in reversed(function_patches):
                setattr(obj, name, original)
            for cls, method_name, raw_descriptor in reversed(patches):
                setattr(cls, method_name, raw_descriptor)


class SecureAirLLMWrapper:
    """Verify exact model + AirLLM source identity, then load behind hard-false gates."""

    def __init__(
        self,
        model_allowlist: Mapping[str, Iterable[str]],
        *,
        loader_source_allowlist: Iterable[str] | None,
        loader: type[_AirLLMLoader] | Any | None = None,
        transformers_module: ModuleType | Any | None = None,
    ) -> None:
        self._allowlist = normalize_allowlist(model_allowlist)
        self._loader_source_allowlist = _normalize_digest_set(
            loader_source_allowlist, label="AirLLM loader source allowlist"
        )
        self._loader = loader
        self._transformers_module = transformers_module

    def verify(self, model_id: str, model_path: str | os.PathLike[str]) -> VerifiedModel:
        return verify_model_allowlist(model_id, model_path, self._allowlist)

    def _resolve_loader(self) -> Any:
        if self._loader is not None:
            return self._loader
        try:
            from airllm import AutoModel  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise AirLLMSecurityError("airllm.AutoModel is unavailable") from exc
        return AutoModel

    def load(
        self,
        model_id: str,
        model_path: str | os.PathLike[str],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        requested_trust = kwargs.pop("trust_remote_code", False)
        if requested_trust is not False:
            raise RemoteCodeTrustError("trust_remote_code must be literal False")
        if kwargs.get("delete_original", False) is not False:
            raise UnsafeLoadOptionError("delete_original=True is not admitted by the secure wrapper")
        kwargs.setdefault("delete_original", False)

        first_model = self.verify(model_id, model_path)
        loader = self._resolve_loader()
        first_source = verify_loader_source(loader, self._loader_source_allowlist)

        # Revalidate after resolution/import work, immediately before the guarded call.
        second_model = self.verify(model_id, model_path)
        second_source = verify_loader_source(loader, self._loader_source_allowlist)
        if first_model != second_model:
            raise ModelIntegrityError("model identity changed before AirLLM invocation")
        if first_source != second_source:
            raise LoaderSourceIntegrityError("AirLLM loader source changed before invocation")

        with hard_false_remote_code_membrane(self._transformers_module):
            return loader.from_pretrained(second_model.path, *args, **kwargs)


__all__ = [
    "AirLLMSecurityError",
    "InvalidAllowlistError",
    "ModelIntegrityError",
    "UnsafeModelArtifactError",
    "LoaderSourceIntegrityError",
    "RemoteCodeTrustError",
    "UnsafeLoadOptionError",
    "VerifiedModel",
    "VerifiedLoaderSource",
    "SecureAirLLMWrapper",
    "hard_false_remote_code_membrane",
    "normalize_allowlist",
    "sha256_loader_source",
    "sha256_model_path",
    "verify_loader_source",
    "verify_model_allowlist",
]
