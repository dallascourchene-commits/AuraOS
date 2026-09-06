"""Generation- and implementation-bound process owner for native AirLLM loading.

The service consumes, but does not authenticate, the current security subject and
semantic-admission surface.  The attested launch path additionally binds the exact
isolation implementation generation and the process/service source bytes observed by
both parent and spawned child.  This prevents a well-formed historical worker receipt
from clearing a newer implementation generation.

The loaded model remains resident in the spawned child.  This is concurrency isolation
and currentness binding, not a hostile-code sandbox, provider oracle, or effect grant.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import importlib
import json
import os
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence

try:
    from . import airllm_process_isolation as _process_isolation_module
    from .airllm_process_isolation import (
        IsolatedObjectProxy,
        IsolationBoundaryError,
        IsolationReceipt,
    )
except ImportError:
    import airllm_process_isolation as _process_isolation_module
    from airllm_process_isolation import (
        IsolatedObjectProxy,
        IsolationBoundaryError,
        IsolationReceipt,
    )

_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_ATTESTED_STATUS_KEYS = frozenset(
    {
        "pid",
        "subject_generation",
        "isolation_implementation_generation",
        "semantic_admission_surface_root",
        "model_id",
        "process_source_sha256",
        "service_source_sha256",
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


def _strict_hex(value: Any, *, bits: int, label: str) -> str:
    pattern = _HEX40 if bits == 160 else _HEX64
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise IsolationBoundaryError(
            f"{label} must be exact lowercase {40 if bits == 160 else 64}-hex"
        )
    return value


def _stable_source_sha256(path: str | os.PathLike[str]) -> str:
    file_path = Path(path).resolve(strict=True)
    before = file_path.stat()
    digest = sha256()
    with file_path.open("rb", buffering=0) as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
        opened = os.fstat(handle.fileno())
    after = file_path.stat()
    before_identity = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    opened_identity = (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns)
    after_identity = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if before_identity != opened_identity or before_identity != after_identity:
        raise IsolationBoundaryError(f"source changed while hashing: {file_path}")
    return digest.hexdigest()


def _public_symbol(module_name: str, qualname: str) -> Any:
    if not isinstance(module_name, str) or not module_name:
        raise IsolationBoundaryError("symbol module must be a non-empty string")
    if not isinstance(qualname, str) or not qualname or "<locals>" in qualname:
        raise IsolationBoundaryError("symbol qualname must be importable")
    obj: Any = importlib.import_module(module_name)
    for part in qualname.split("."):
        if not part or part.startswith("_"):
            raise IsolationBoundaryError("private symbol paths are not admitted")
        obj = getattr(obj, part)
    return obj


def _optional_symbol(spec: tuple[str, str] | None) -> Any | None:
    if spec is None:
        return None
    if not isinstance(spec, tuple) or len(spec) != 2:
        raise IsolationBoundaryError("symbol specs must be (module, qualname) tuples")
    return _public_symbol(spec[0], spec[1])


@dataclass(frozen=True)
class CurrentIsolationBinding:
    subject_generation: str
    semantic_admission_surface_root: str
    model_id: str
    currentness_root: str


@dataclass(frozen=True)
class ImplementationSourceIdentity:
    process_source_sha256: str
    service_source_sha256: str


@dataclass(frozen=True)
class CurrentIsolationAdmission:
    subject_generation: str
    isolation_implementation_generation: str
    semantic_admission_surface_root: str
    model_id: str
    process_source_sha256: str
    service_source_sha256: str
    currentness_root: str
    authority_ceiling: str = "D0_PROCESS_ISOLATION_ONLY"


def bind_current_isolation_surface(
    subject_generation: str,
    semantic_admission_surface_root: str,
    model_id: str,
) -> CurrentIsolationBinding:
    """V1 compatibility binding for the security subject + semantic surface."""
    _strict_hex(subject_generation, bits=160, label="subject_generation")
    _strict_hex(
        semantic_admission_surface_root,
        bits=256,
        label="semantic_admission_surface_root",
    )
    if not isinstance(model_id, str) or not model_id or model_id.strip() != model_id:
        raise IsolationBoundaryError("model_id must be a non-empty exact string")
    payload = {
        "schema": "AURA-AIRLLM-ISOLATION-CURRENTNESS-v1",
        "subject_generation": subject_generation,
        "semantic_admission_surface_root": semantic_admission_surface_root,
        "model_id": model_id,
    }
    return CurrentIsolationBinding(
        subject_generation=subject_generation,
        semantic_admission_surface_root=semantic_admission_surface_root,
        model_id=model_id,
        currentness_root=sha256(_canonical_json(payload)).hexdigest(),
    )


def current_implementation_source_identity() -> ImplementationSourceIdentity:
    process_path = getattr(_process_isolation_module, "__file__", None)
    if not process_path or not __file__:
        raise IsolationBoundaryError("implementation source paths are unavailable")
    return ImplementationSourceIdentity(
        process_source_sha256=_stable_source_sha256(process_path),
        service_source_sha256=_stable_source_sha256(__file__),
    )


def bind_current_isolation_admission(
    subject_generation: str,
    isolation_implementation_generation: str,
    semantic_admission_surface_root: str,
    model_id: str,
    *,
    process_source_sha256: str | None = None,
    service_source_sha256: str | None = None,
) -> CurrentIsolationAdmission:
    """Bind session, subject and implementation currentness as noncompensatory axes."""
    _strict_hex(subject_generation, bits=160, label="subject_generation")
    _strict_hex(
        isolation_implementation_generation,
        bits=160,
        label="isolation_implementation_generation",
    )
    _strict_hex(
        semantic_admission_surface_root,
        bits=256,
        label="semantic_admission_surface_root",
    )
    if not isinstance(model_id, str) or not model_id or model_id.strip() != model_id:
        raise IsolationBoundaryError("model_id must be a non-empty exact string")
    if process_source_sha256 is None or service_source_sha256 is None:
        identity = current_implementation_source_identity()
        process_source_sha256 = identity.process_source_sha256
        service_source_sha256 = identity.service_source_sha256
    _strict_hex(process_source_sha256, bits=256, label="process_source_sha256")
    _strict_hex(service_source_sha256, bits=256, label="service_source_sha256")
    payload = {
        "schema": "AURA-AIRLLM-ISOLATION-CURRENTNESS-v2",
        "subject_generation": subject_generation,
        "isolation_implementation_generation": isolation_implementation_generation,
        "semantic_admission_surface_root": semantic_admission_surface_root,
        "model_id": model_id,
        "process_source_sha256": process_source_sha256,
        "service_source_sha256": service_source_sha256,
        "authority_ceiling": "D0_PROCESS_ISOLATION_ONLY",
    }
    return CurrentIsolationAdmission(
        subject_generation=subject_generation,
        isolation_implementation_generation=isolation_implementation_generation,
        semantic_admission_surface_root=semantic_admission_surface_root,
        model_id=model_id,
        process_source_sha256=process_source_sha256,
        service_source_sha256=service_source_sha256,
        currentness_root=sha256(_canonical_json(payload)).hexdigest(),
    )


class IsolatedNativeAirLLMService:
    """Child-owned wrapper + loaded-model lifetime for native AirLLM compatibility."""

    def __init__(
        self,
        model_id: str,
        model_path: str,
        model_allowlist: Mapping[str, Iterable[str]],
        loader_source_allowlist: Iterable[str] | None,
        loader_package_source_allowlist: Iterable[str] | None,
        subject_generation: str,
        semantic_admission_surface_root: str,
        *,
        isolation_implementation_generation: str | None = None,
        expected_process_source_sha256: str | None = None,
        expected_service_source_sha256: str | None = None,
        loader_package_required_paths: Sequence[str] | None = None,
        load_args: tuple[Any, ...] = (),
        load_kwargs: Mapping[str, Any] | None = None,
        loader_symbol: tuple[str, str] | None = None,
        transformers_symbol: tuple[str, str] | None = None,
        wrapper_symbol: tuple[str, str] = (
            "airllm_native_compat_wrapper",
            "ManifestPinnedNativeAirLLMWrapper",
        ),
    ) -> None:
        self._binding = bind_current_isolation_surface(
            subject_generation,
            semantic_admission_surface_root,
            model_id,
        )
        self._admission: CurrentIsolationAdmission | None = None
        if isolation_implementation_generation is not None:
            if expected_process_source_sha256 is None or expected_service_source_sha256 is None:
                raise IsolationBoundaryError(
                    "attested isolation requires expected process and service source hashes"
                )
            observed = current_implementation_source_identity()
            if observed.process_source_sha256 != expected_process_source_sha256:
                raise IsolationBoundaryError(
                    "child process-isolation source identity differs from parent expectation"
                )
            if observed.service_source_sha256 != expected_service_source_sha256:
                raise IsolationBoundaryError(
                    "child native-service source identity differs from parent expectation"
                )
            self._admission = bind_current_isolation_admission(
                subject_generation,
                isolation_implementation_generation,
                semantic_admission_surface_root,
                model_id,
                process_source_sha256=observed.process_source_sha256,
                service_source_sha256=observed.service_source_sha256,
            )

        wrapper_type = _optional_symbol(wrapper_symbol)
        if wrapper_type is None:
            raise IsolationBoundaryError("native wrapper symbol is required")
        loader = _optional_symbol(loader_symbol)
        transformers_module = _optional_symbol(transformers_symbol)
        wrapper = wrapper_type(
            model_allowlist,
            loader_source_allowlist=loader_source_allowlist,
            loader_package_source_allowlist=loader_package_source_allowlist,
            loader_package_required_paths=loader_package_required_paths,
            loader=loader,
            transformers_module=transformers_module,
        )
        kwargs = {} if load_kwargs is None else dict(load_kwargs)
        self._loaded = wrapper.load(model_id, model_path, *tuple(load_args), **kwargs)

    def status(self) -> dict[str, Any]:
        base = {
            "pid": os.getpid(),
            "subject_generation": self._binding.subject_generation,
            "semantic_admission_surface_root": self._binding.semantic_admission_surface_root,
            "model_id": self._binding.model_id,
            "currentness_root": self._binding.currentness_root,
        }
        if self._admission is None:
            return base
        return {
            "pid": os.getpid(),
            "subject_generation": self._admission.subject_generation,
            "isolation_implementation_generation": self._admission.isolation_implementation_generation,
            "semantic_admission_surface_root": self._admission.semantic_admission_surface_root,
            "model_id": self._admission.model_id,
            "process_source_sha256": self._admission.process_source_sha256,
            "service_source_sha256": self._admission.service_source_sha256,
            "currentness_root": self._admission.currentness_root,
            "authority_ceiling": self._admission.authority_ceiling,
        }

    def generate(self, *args: Any, **kwargs: Any) -> Any:
        method = getattr(self._loaded, "generate", None)
        if not callable(method):
            raise IsolationBoundaryError("loaded AirLLM object has no callable generate boundary")
        return method(*args, **kwargs)

    def close(self) -> None:
        closer = getattr(self._loaded, "close", None)
        if callable(closer):
            closer()


def _launch_proxy(
    model_id: str,
    model_path: str,
    model_allowlist: Mapping[str, Iterable[str]],
    loader_source_allowlist: Iterable[str] | None,
    loader_package_source_allowlist: Iterable[str] | None,
    subject_generation: str,
    semantic_admission_surface_root: str,
    *,
    isolation_implementation_generation: str | None,
    expected_process_source_sha256: str | None,
    expected_service_source_sha256: str | None,
    loader_package_required_paths: Sequence[str] | None,
    load_args: tuple[Any, ...],
    load_kwargs: Mapping[str, Any] | None,
    loader_symbol: tuple[str, str] | None,
    transformers_symbol: tuple[str, str] | None,
    wrapper_symbol: tuple[str, str],
    timeout_seconds: float,
) -> IsolatedObjectProxy:
    return IsolatedObjectProxy(
        __name__,
        "IsolatedNativeAirLLMService",
        model_id,
        model_path,
        dict(model_allowlist),
        None if loader_source_allowlist is None else tuple(loader_source_allowlist),
        None if loader_package_source_allowlist is None else tuple(loader_package_source_allowlist),
        subject_generation,
        semantic_admission_surface_root,
        isolation_implementation_generation=isolation_implementation_generation,
        expected_process_source_sha256=expected_process_source_sha256,
        expected_service_source_sha256=expected_service_source_sha256,
        loader_package_required_paths=(
            None if loader_package_required_paths is None
            else tuple(loader_package_required_paths)
        ),
        load_args=tuple(load_args),
        load_kwargs={} if load_kwargs is None else dict(load_kwargs),
        loader_symbol=loader_symbol,
        transformers_symbol=transformers_symbol,
        wrapper_symbol=wrapper_symbol,
        timeout_seconds=timeout_seconds,
    )


def launch_isolated_native_airllm(
    model_id: str,
    model_path: str,
    model_allowlist: Mapping[str, Iterable[str]],
    loader_source_allowlist: Iterable[str] | None,
    loader_package_source_allowlist: Iterable[str] | None,
    subject_generation: str,
    semantic_admission_surface_root: str,
    *,
    loader_package_required_paths: Sequence[str] | None = None,
    load_args: tuple[Any, ...] = (),
    load_kwargs: Mapping[str, Any] | None = None,
    loader_symbol: tuple[str, str] | None = None,
    transformers_symbol: tuple[str, str] | None = None,
    wrapper_symbol: tuple[str, str] = (
        "airllm_native_compat_wrapper",
        "ManifestPinnedNativeAirLLMWrapper",
    ),
    timeout_seconds: float = 30.0,
) -> IsolatedObjectProxy:
    """V1 compatibility launch: child-owned model with subject/surface echo validation."""
    expected = bind_current_isolation_surface(
        subject_generation,
        semantic_admission_surface_root,
        model_id,
    )
    proxy = _launch_proxy(
        model_id,
        model_path,
        model_allowlist,
        loader_source_allowlist,
        loader_package_source_allowlist,
        subject_generation,
        semantic_admission_surface_root,
        isolation_implementation_generation=None,
        expected_process_source_sha256=None,
        expected_service_source_sha256=None,
        loader_package_required_paths=loader_package_required_paths,
        load_args=load_args,
        load_kwargs=load_kwargs,
        loader_symbol=loader_symbol,
        transformers_symbol=transformers_symbol,
        wrapper_symbol=wrapper_symbol,
        timeout_seconds=timeout_seconds,
    )
    try:
        status = proxy.call("status")
        if (
            status.get("pid") != proxy.receipt.child_pid
            or status.get("subject_generation") != expected.subject_generation
            or status.get("semantic_admission_surface_root")
            != expected.semantic_admission_surface_root
            or status.get("model_id") != expected.model_id
            or status.get("currentness_root") != expected.currentness_root
        ):
            raise IsolationBoundaryError("child currentness binding did not match requested surface")
        return proxy
    except BaseException:
        proxy.close()
        raise


def validate_attested_isolation_status(
    status: Mapping[str, Any],
    receipt: IsolationReceipt,
    expected: CurrentIsolationAdmission,
) -> None:
    """Fail closed unless direct child evidence exactly matches the expected admission.

    The exact-key check is deliberate: shared-memory corroboration counts, cached trust
    labels, authority hints, or other derived evidence cannot hitchhike across this
    owner boundary and become part of the admission decision.
    """
    if type(status) is not dict or frozenset(status) != _ATTESTED_STATUS_KEYS:
        raise IsolationBoundaryError("attested child status schema is not exact")
    if status["pid"] != receipt.child_pid or receipt.parent_pid != os.getpid():
        raise IsolationBoundaryError("attested child process identity mismatch")
    if receipt.start_method != "spawn" or receipt.generation <= 0:
        raise IsolationBoundaryError("attested process receipt is not a spawned current session")
    for field in ("worker_nonce_root", "factory_identity_root", "receipt_root"):
        value = getattr(receipt, field, None)
        if not isinstance(value, str) or _HEX64.fullmatch(value) is None:
            raise IsolationBoundaryError(f"attested process receipt has invalid {field}")
    expected_fields = {
        "subject_generation": expected.subject_generation,
        "isolation_implementation_generation": expected.isolation_implementation_generation,
        "semantic_admission_surface_root": expected.semantic_admission_surface_root,
        "model_id": expected.model_id,
        "process_source_sha256": expected.process_source_sha256,
        "service_source_sha256": expected.service_source_sha256,
        "currentness_root": expected.currentness_root,
        "authority_ceiling": expected.authority_ceiling,
    }
    for field, value in expected_fields.items():
        if status[field] != value:
            raise IsolationBoundaryError(f"attested child status mismatch: {field}")
    recomputed = bind_current_isolation_admission(
        status["subject_generation"],
        status["isolation_implementation_generation"],
        status["semantic_admission_surface_root"],
        status["model_id"],
        process_source_sha256=status["process_source_sha256"],
        service_source_sha256=status["service_source_sha256"],
    )
    if recomputed.currentness_root != status["currentness_root"]:
        raise IsolationBoundaryError("attested child currentness root does not recompute")


def launch_attested_isolated_native_airllm(
    model_id: str,
    model_path: str,
    model_allowlist: Mapping[str, Iterable[str]],
    loader_source_allowlist: Iterable[str] | None,
    loader_package_source_allowlist: Iterable[str] | None,
    subject_generation: str,
    isolation_implementation_generation: str,
    semantic_admission_surface_root: str,
    *,
    loader_package_required_paths: Sequence[str] | None = None,
    load_args: tuple[Any, ...] = (),
    load_kwargs: Mapping[str, Any] | None = None,
    loader_symbol: tuple[str, str] | None = None,
    transformers_symbol: tuple[str, str] | None = None,
    wrapper_symbol: tuple[str, str] = (
        "airllm_native_compat_wrapper",
        "ManifestPinnedNativeAirLLMWrapper",
    ),
    timeout_seconds: float = 30.0,
) -> IsolatedObjectProxy:
    """Launch only when parent and child agree on subject + implementation bytes."""
    identity = current_implementation_source_identity()
    expected = bind_current_isolation_admission(
        subject_generation,
        isolation_implementation_generation,
        semantic_admission_surface_root,
        model_id,
        process_source_sha256=identity.process_source_sha256,
        service_source_sha256=identity.service_source_sha256,
    )
    proxy = _launch_proxy(
        model_id,
        model_path,
        model_allowlist,
        loader_source_allowlist,
        loader_package_source_allowlist,
        subject_generation,
        semantic_admission_surface_root,
        isolation_implementation_generation=isolation_implementation_generation,
        expected_process_source_sha256=identity.process_source_sha256,
        expected_service_source_sha256=identity.service_source_sha256,
        loader_package_required_paths=loader_package_required_paths,
        load_args=load_args,
        load_kwargs=load_kwargs,
        loader_symbol=loader_symbol,
        transformers_symbol=transformers_symbol,
        wrapper_symbol=wrapper_symbol,
        timeout_seconds=timeout_seconds,
    )
    try:
        status = proxy.call("status")
        validate_attested_isolation_status(status, proxy.receipt, expected)
        return proxy
    except BaseException:
        proxy.close()
        raise


__all__ = [
    "CurrentIsolationAdmission",
    "CurrentIsolationBinding",
    "ImplementationSourceIdentity",
    "IsolatedNativeAirLLMService",
    "bind_current_isolation_admission",
    "bind_current_isolation_surface",
    "current_implementation_source_identity",
    "launch_attested_isolated_native_airllm",
    "launch_isolated_native_airllm",
    "validate_attested_isolation_status",
]
