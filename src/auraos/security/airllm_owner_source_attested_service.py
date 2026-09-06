"""Owner-source-attested process isolation layered on the PR #844 v1 service.

This additive boundary closes one direct currentness gap without rewriting the already
proved process/service primitive: the executing AuraOS security wrapper stack is hashed
as a deterministic owner-source manifest in both parent and spawned child before wrapper
construction.  Shared-memory repetition remains non-authoritative; status admission is
exact-schema and D0 only.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import importlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Iterable, Mapping, Sequence

try:
    from .airllm_process_isolation import IsolatedObjectProxy, IsolationBoundaryError, IsolationReceipt
    from .airllm_isolated_native_service import (
        IsolatedNativeAirLLMService,
        current_implementation_source_identity,
    )
except ImportError:
    from airllm_process_isolation import IsolatedObjectProxy, IsolationBoundaryError, IsolationReceipt
    from airllm_isolated_native_service import (
        IsolatedNativeAirLLMService,
        current_implementation_source_identity,
    )

_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_DEFAULT_WRAPPER_SYMBOL = (
    "airllm_native_compat_wrapper",
    "ManifestPinnedNativeAirLLMWrapper",
)
_DEFAULT_SECURITY_MODULES = (
    "airllm_native_compat_wrapper",
    "airllm_manifest_pinned_wrapper",
    "airllm_secure_wrapper",
    "airllm_source_manifest_guard",
)
_STATUS_KEYS = frozenset(
    {
        "pid",
        "subject_generation",
        "isolation_implementation_generation",
        "semantic_admission_surface_root",
        "model_id",
        "process_source_sha256",
        "service_source_sha256",
        "owner_source_manifest_root",
        "currentness_root",
        "authority_ceiling",
    }
)


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _hex(value: Any, size: int, label: str) -> str:
    pattern = _HEX40 if size == 40 else _HEX64
    if type(value) is not str or pattern.fullmatch(value) is None:
        raise IsolationBoundaryError(f"{label} must be exact lowercase {size}-hex")
    return value


def _stable_sha256(path: str) -> str:
    resolved = Path(path).resolve(strict=True)
    before = resolved.stat()
    digest = sha256()
    with resolved.open("rb", buffering=0) as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
        opened = os.fstat(handle.fileno())
    after = resolved.stat()
    identities = {
        (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns),
        (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns),
        (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns),
    }
    if len(identities) != 1:
        raise IsolationBoundaryError(f"owner source changed while hashing: {resolved}")
    return digest.hexdigest()


def _normalize_modules(
    wrapper_symbol: tuple[str, str],
    modules: Sequence[str] | None,
) -> tuple[str, ...]:
    requested = (
        _DEFAULT_SECURITY_MODULES
        if modules is None and wrapper_symbol == _DEFAULT_WRAPPER_SYMBOL
        else ((wrapper_symbol[0],) if modules is None else tuple(modules))
    )
    ordered = (__name__,) + tuple(name for name in requested if name != __name__)
    if any(type(name) is not str or not name or name.strip() != name for name in ordered):
        raise IsolationBoundaryError("owner source modules must be exact non-empty names")
    if len(set(ordered)) != len(ordered):
        raise IsolationBoundaryError("owner source modules must be unique")
    return ordered


def _module_sha256(module_name: str, *, loaded: bool) -> str:
    if loaded:
        module = importlib.import_module(module_name)
        origin = getattr(module, "__file__", None)
    else:
        spec = importlib.util.find_spec(module_name)
        origin = None if spec is None else spec.origin
    if type(origin) is not str or not origin or origin in {"built-in", "frozen"}:
        raise IsolationBoundaryError(f"owner module origin unavailable: {module_name}")
    return _stable_sha256(origin)


def owner_source_manifest_root(modules: Sequence[str], *, loaded: bool = False) -> str:
    normalized = tuple(modules)
    if not normalized or len(set(normalized)) != len(normalized):
        raise IsolationBoundaryError("owner source manifest requires unique modules")
    entries = [
        {"module": name, "sha256": _module_sha256(name, loaded=loaded)}
        for name in normalized
    ]
    return sha256(
        _canonical_json(
            {"schema": "AURA-AIRLLM-OWNER-SOURCE-MANIFEST-v1", "modules": entries}
        )
    ).hexdigest()


@dataclass(frozen=True)
class OwnerIsolationAdmission:
    subject_generation: str
    isolation_implementation_generation: str
    semantic_admission_surface_root: str
    model_id: str
    process_source_sha256: str
    service_source_sha256: str
    owner_source_manifest_root: str
    currentness_root: str
    authority_ceiling: str = "D0_PROCESS_ISOLATION_ONLY"


def bind_owner_isolation_admission(
    subject_generation: str,
    isolation_implementation_generation: str,
    semantic_admission_surface_root: str,
    model_id: str,
    process_source_sha256: str,
    service_source_sha256: str,
    owner_manifest_root: str,
) -> OwnerIsolationAdmission:
    _hex(subject_generation, 40, "subject_generation")
    _hex(isolation_implementation_generation, 40, "isolation_implementation_generation")
    _hex(semantic_admission_surface_root, 64, "semantic_admission_surface_root")
    _hex(process_source_sha256, 64, "process_source_sha256")
    _hex(service_source_sha256, 64, "service_source_sha256")
    _hex(owner_manifest_root, 64, "owner_source_manifest_root")
    if type(model_id) is not str or not model_id or model_id.strip() != model_id:
        raise IsolationBoundaryError("model_id must be an exact non-empty string")
    body = {
        "schema": "AURA-AIRLLM-OWNER-ISOLATION-CURRENTNESS-v1",
        "subject_generation": subject_generation,
        "isolation_implementation_generation": isolation_implementation_generation,
        "semantic_admission_surface_root": semantic_admission_surface_root,
        "model_id": model_id,
        "process_source_sha256": process_source_sha256,
        "service_source_sha256": service_source_sha256,
        "owner_source_manifest_root": owner_manifest_root,
        "authority_ceiling": "D0_PROCESS_ISOLATION_ONLY",
    }
    return OwnerIsolationAdmission(
        subject_generation,
        isolation_implementation_generation,
        semantic_admission_surface_root,
        model_id,
        process_source_sha256,
        service_source_sha256,
        owner_manifest_root,
        sha256(_canonical_json(body)).hexdigest(),
    )


class OwnerSourceAttestedService:
    """Child-resident wrapper guarded by parent/child owner-source parity."""

    def __init__(
        self,
        model_id: str,
        model_path: str,
        model_allowlist: Mapping[str, Iterable[str]],
        loader_source_allowlist: Iterable[str] | None,
        loader_package_source_allowlist: Iterable[str] | None,
        subject_generation: str,
        isolation_implementation_generation: str,
        semantic_admission_surface_root: str,
        expected_process_source_sha256: str,
        expected_service_source_sha256: str,
        expected_owner_source_manifest_root: str,
        owner_source_modules: Sequence[str],
        *,
        loader_package_required_paths: Sequence[str] | None = None,
        load_args: tuple[Any, ...] = (),
        load_kwargs: Mapping[str, Any] | None = None,
        loader_symbol: tuple[str, str] | None = None,
        transformers_symbol: tuple[str, str] | None = None,
        wrapper_symbol: tuple[str, str] = _DEFAULT_WRAPPER_SYMBOL,
    ) -> None:
        identity = current_implementation_source_identity()
        if identity.process_source_sha256 != expected_process_source_sha256:
            raise IsolationBoundaryError("child process source differs from parent expectation")
        if identity.service_source_sha256 != expected_service_source_sha256:
            raise IsolationBoundaryError("child service source differs from parent expectation")
        modules = _normalize_modules(wrapper_symbol, owner_source_modules)
        if owner_source_manifest_root(modules, loaded=False) != expected_owner_source_manifest_root:
            raise IsolationBoundaryError("child owner-source manifest differs before import")
        for module_name in modules:
            importlib.import_module(module_name)
        loaded_root = owner_source_manifest_root(modules, loaded=True)
        if loaded_root != expected_owner_source_manifest_root:
            raise IsolationBoundaryError("child owner-source manifest differs after import")
        self._admission = bind_owner_isolation_admission(
            subject_generation,
            isolation_implementation_generation,
            semantic_admission_surface_root,
            model_id,
            identity.process_source_sha256,
            identity.service_source_sha256,
            loaded_root,
        )
        self._inner = IsolatedNativeAirLLMService(
            model_id,
            model_path,
            model_allowlist,
            loader_source_allowlist,
            loader_package_source_allowlist,
            subject_generation,
            semantic_admission_surface_root,
            loader_package_required_paths=loader_package_required_paths,
            load_args=load_args,
            load_kwargs=load_kwargs,
            loader_symbol=loader_symbol,
            transformers_symbol=transformers_symbol,
            wrapper_symbol=wrapper_symbol,
        )

    def status(self) -> dict[str, Any]:
        a = self._admission
        return {
            "pid": os.getpid(),
            "subject_generation": a.subject_generation,
            "isolation_implementation_generation": a.isolation_implementation_generation,
            "semantic_admission_surface_root": a.semantic_admission_surface_root,
            "model_id": a.model_id,
            "process_source_sha256": a.process_source_sha256,
            "service_source_sha256": a.service_source_sha256,
            "owner_source_manifest_root": a.owner_source_manifest_root,
            "currentness_root": a.currentness_root,
            "authority_ceiling": a.authority_ceiling,
        }

    def generate(self, *args: Any, **kwargs: Any) -> Any:
        return self._inner.generate(*args, **kwargs)

    def close(self) -> None:
        self._inner.close()


def validate_owner_attested_status(
    status: Mapping[str, Any],
    receipt: IsolationReceipt,
    expected: OwnerIsolationAdmission,
) -> None:
    if type(status) is not dict or frozenset(status) != _STATUS_KEYS:
        raise IsolationBoundaryError("owner-attested child status schema is not exact")
    if status["pid"] != receipt.child_pid or receipt.parent_pid != os.getpid():
        raise IsolationBoundaryError("owner-attested process identity mismatch")
    if receipt.start_method not in {"spawn", "subprocess-source-attested-v1"} or receipt.generation <= 0:
        raise IsolationBoundaryError("owner-attested receipt is not a current isolated session")
    expected_fields = {
        "subject_generation": expected.subject_generation,
        "isolation_implementation_generation": expected.isolation_implementation_generation,
        "semantic_admission_surface_root": expected.semantic_admission_surface_root,
        "model_id": expected.model_id,
        "process_source_sha256": expected.process_source_sha256,
        "service_source_sha256": expected.service_source_sha256,
        "owner_source_manifest_root": expected.owner_source_manifest_root,
        "currentness_root": expected.currentness_root,
        "authority_ceiling": expected.authority_ceiling,
    }
    for field, value in expected_fields.items():
        if status[field] != value:
            raise IsolationBoundaryError(f"owner-attested child status mismatch: {field}")
    recomputed = bind_owner_isolation_admission(
        status["subject_generation"],
        status["isolation_implementation_generation"],
        status["semantic_admission_surface_root"],
        status["model_id"],
        status["process_source_sha256"],
        status["service_source_sha256"],
        status["owner_source_manifest_root"],
    )
    if recomputed.currentness_root != status["currentness_root"]:
        raise IsolationBoundaryError("owner-attested currentness root does not recompute")


def launch_owner_attested_airllm(
    model_id: str,
    model_path: str,
    model_allowlist: Mapping[str, Iterable[str]],
    loader_source_allowlist: Iterable[str] | None,
    loader_package_source_allowlist: Iterable[str] | None,
    subject_generation: str,
    isolation_implementation_generation: str,
    semantic_admission_surface_root: str,
    *,
    owner_source_modules: Sequence[str] | None = None,
    loader_package_required_paths: Sequence[str] | None = None,
    load_args: tuple[Any, ...] = (),
    load_kwargs: Mapping[str, Any] | None = None,
    loader_symbol: tuple[str, str] | None = None,
    transformers_symbol: tuple[str, str] | None = None,
    wrapper_symbol: tuple[str, str] = _DEFAULT_WRAPPER_SYMBOL,
    timeout_seconds: float = 30.0,
) -> IsolatedObjectProxy:
    identity = current_implementation_source_identity()
    modules = _normalize_modules(wrapper_symbol, owner_source_modules)
    owner_root = owner_source_manifest_root(modules, loaded=False)
    expected = bind_owner_isolation_admission(
        subject_generation,
        isolation_implementation_generation,
        semantic_admission_surface_root,
        model_id,
        identity.process_source_sha256,
        identity.service_source_sha256,
        owner_root,
    )
    try:
        from .airllm_preimport_source_proxy import PreimportSourceObjectProxy
    except ImportError:
        from airllm_preimport_source_proxy import PreimportSourceObjectProxy
    target_source_path = str(Path(__file__).resolve(strict=True))
    target_source_sha256 = _stable_sha256(target_source_path)
    import_roots = tuple(
        str(Path(entry).resolve())
        for entry in sys.path
        if isinstance(entry, str) and entry and Path(entry).exists() and Path(entry).is_dir()
    )
    proxy = PreimportSourceObjectProxy(
        __name__,
        "OwnerSourceAttestedService",
        target_source_path,
        target_source_sha256,
        model_id,
        model_path,
        dict(model_allowlist),
        None if loader_source_allowlist is None else tuple(loader_source_allowlist),
        None if loader_package_source_allowlist is None else tuple(loader_package_source_allowlist),
        subject_generation,
        isolation_implementation_generation,
        semantic_admission_surface_root,
        identity.process_source_sha256,
        identity.service_source_sha256,
        owner_root,
        modules,
        loader_package_required_paths=(
            None if loader_package_required_paths is None else tuple(loader_package_required_paths)
        ),
        load_args=tuple(load_args),
        load_kwargs={} if load_kwargs is None else dict(load_kwargs),
        loader_symbol=loader_symbol,
        transformers_symbol=transformers_symbol,
        wrapper_symbol=wrapper_symbol,
        import_roots=import_roots,
        timeout_seconds=timeout_seconds,
    )
    try:
        status = proxy.call("status")
        validate_owner_attested_status(status, proxy.receipt, expected)
        return proxy
    except BaseException:
        proxy.close()
        raise


__all__ = [
    "OwnerIsolationAdmission",
    "OwnerSourceAttestedService",
    "bind_owner_isolation_admission",
    "launch_owner_attested_airllm",
    "owner_source_manifest_root",
    "validate_owner_attested_status",
]
