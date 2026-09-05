"""Fail-closed AirLLM loading membrane.

Security contract:
- model bytes must be local and match an exact SHA-256 allowlist;
- symbolic links and non-regular artifacts are rejected;
- every guarded Transformers loader boundary receives ``trust_remote_code=False``;
- any attempt to widen ``trust_remote_code`` aborts the load;
- destructive ``delete_original=True`` requests are rejected.

The wrapper does not make an untrusted/custom-code model safe. If a model requires
remote Python code, the load fails closed instead of opting in.
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
import threading
from types import ModuleType
from typing import Any, Iterable, Mapping, Protocol

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_DIRECTORY_DIGEST_SCHEMA = "AURA-MODEL-DIR-SHA256-v1"
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


def normalize_allowlist(allowlist: Mapping[str, Iterable[str]]) -> dict[str, frozenset[str]]:
    """Copy and strictly validate a model-id -> exact SHA-256 allowlist mapping."""
    if not isinstance(allowlist, Mapping) or not allowlist:
        raise InvalidAllowlistError("model allowlist must be a non-empty mapping")
    normalized: dict[str, frozenset[str]] = {}
    for model_id, digests in allowlist.items():
        if not isinstance(model_id, str) or not model_id or model_id.strip() != model_id:
            raise InvalidAllowlistError("model ids must be non-empty exact strings")
        if isinstance(digests, (str, bytes)):
            raise InvalidAllowlistError("each model id must map to a collection of SHA-256 values")
        try:
            values = frozenset(_validate_digest(value) for value in digests)
        except TypeError as exc:
            raise InvalidAllowlistError("each model id must map to an iterable of SHA-256 values") from exc
        if not values:
            raise InvalidAllowlistError(f"model {model_id!r} has an empty digest allowlist")
        normalized[model_id] = values
    return normalized


def _assert_regular_local_file(path: Path) -> os.stat_result:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise ModelIntegrityError(f"model artifact is not readable: {path}") from exc
    if stat.S_ISLNK(metadata.st_mode):
        raise ModelIntegrityError(f"symbolic links are not admitted: {path}")
    if not stat.S_ISREG(metadata.st_mode):
        raise ModelIntegrityError(f"model artifact must be a regular file: {path}")
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
                raise ModelIntegrityError(f"model artifact changed before hashing: {path}")
            while True:
                chunk = handle.read(chunk_size)
                if not chunk:
                    break
                digest.update(chunk)
            after_open = os.fstat(handle.fileno())
    except ModelIntegrityError:
        raise
    except OSError as exc:
        raise ModelIntegrityError(f"failed while hashing model artifact: {path}") from exc
    try:
        after_path = path.lstat()
    except OSError as exc:
        raise ModelIntegrityError(f"model artifact disappeared after hashing: {path}") from exc
    identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    identity_opened = (after_open.st_dev, after_open.st_ino, after_open.st_size, after_open.st_mtime_ns)
    identity_after = (after_path.st_dev, after_path.st_ino, after_path.st_size, after_path.st_mtime_ns)
    if identity_before != identity_opened or identity_before != identity_after:
        raise ModelIntegrityError(f"model artifact changed while hashing: {path}")
    return digest.hexdigest()


def sha256_model_path(model_path: str | os.PathLike[str]) -> tuple[str, str]:
    """Return (digest, kind) for a local model file or canonical directory manifest.

    Directory identity is the SHA-256 of a canonical manifest containing every regular
    file's relative POSIX path, byte length, and content SHA-256. Symlinks, special files,
    empty directories, and path traversal are rejected.
    """
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
        return _sha256_regular_file(path), "file"
    if not stat.S_ISDIR(root_meta.st_mode):
        raise ModelIntegrityError(f"model path must be a regular file or directory: {path}")

    files: list[dict[str, Any]] = []
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
        relative = candidate.relative_to(path).as_posix()
        if relative.startswith("../") or relative == "..":
            raise ModelIntegrityError("model directory traversal detected")
        file_digest = _sha256_regular_file(candidate)
        files.append({"path": relative, "size": metadata.st_size, "sha256": file_digest})
    if not files:
        raise ModelIntegrityError("empty model directories are not admitted")
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


def _resolve_transformers_module(transformers_module: ModuleType | Any | None) -> Any:
    if transformers_module is not None:
        return transformers_module
    try:
        import transformers  # type: ignore
    except Exception as exc:  # pragma: no cover - exercised through dependency injection in unit tests
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
    """Temporarily force known Transformers model-loading boundaries to hard-false.

    The membrane is process-global while active, therefore guarded loads are serialized.
    Every patched boundary rejects an explicit value other than literal ``False`` and
    injects ``trust_remote_code=False`` when the caller omitted it.
    """
    module = _resolve_transformers_module(transformers_module)
    patches: list[tuple[Any, str, Any]] = []
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
            if not patches:
                raise RemoteCodeTrustError("no supported Transformers loader boundaries were found")
            yield
        finally:
            for cls, method_name, raw_descriptor in reversed(patches):
                setattr(cls, method_name, raw_descriptor)


class SecureAirLLMWrapper:
    """Verify exact model identity, then invoke AirLLM behind a hard-false membrane."""

    def __init__(
        self,
        model_allowlist: Mapping[str, Iterable[str]],
        *,
        loader: type[_AirLLMLoader] | Any | None = None,
        transformers_module: ModuleType | Any | None = None,
    ) -> None:
        self._allowlist = normalize_allowlist(model_allowlist)
        self._loader = loader
        self._transformers_module = transformers_module

    def verify(self, model_id: str, model_path: str | os.PathLike[str]) -> VerifiedModel:
        return verify_model_allowlist(model_id, model_path, self._allowlist)

    def _resolve_loader(self) -> Any:
        if self._loader is not None:
            return self._loader
        try:
            from airllm import AutoModel  # type: ignore
        except Exception as exc:  # pragma: no cover - exercised through dependency injection in unit tests
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

        verified = self.verify(model_id, model_path)
        loader = self._resolve_loader()
        with hard_false_remote_code_membrane(self._transformers_module):
            return loader.from_pretrained(verified.path, *args, **kwargs)


__all__ = [
    "AirLLMSecurityError",
    "InvalidAllowlistError",
    "ModelIntegrityError",
    "RemoteCodeTrustError",
    "UnsafeLoadOptionError",
    "VerifiedModel",
    "SecureAirLLMWrapper",
    "hard_false_remote_code_membrane",
    "normalize_allowlist",
    "sha256_model_path",
    "verify_model_allowlist",
]
