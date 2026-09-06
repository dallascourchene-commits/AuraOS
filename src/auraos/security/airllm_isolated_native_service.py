"""Generation-bound process owner for the manifest-pinned native AirLLM load path.

The service intentionally consumes, but does not authenticate, a subject generation and
semantic-admission-surface root. They prevent a well-formed historical isolation receipt
from being reused as if it described the current security generation.

The loaded model remains in the spawned child. This closes the *concurrency ownership*
problem for process-global compatibility patches when integrated with the real wrapper;
it is not a hostile-code sandbox or a provider/currentness oracle.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import importlib
import json
import os
import re
from typing import Any, Iterable, Mapping, Sequence

try:
    from .airllm_process_isolation import IsolatedObjectProxy, IsolationBoundaryError
except ImportError:
    from airllm_process_isolation import IsolatedObjectProxy, IsolationBoundaryError

_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


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


def bind_current_isolation_surface(
    subject_generation: str,
    semantic_admission_surface_root: str,
    model_id: str,
) -> CurrentIsolationBinding:
    """Bind an opaque currentness surface to the exact security subject generation."""
    if not isinstance(subject_generation, str) or _HEX40.fullmatch(subject_generation) is None:
        raise IsolationBoundaryError("subject_generation must be exact lowercase 40-hex")
    if (
        not isinstance(semantic_admission_surface_root, str)
        or _HEX64.fullmatch(semantic_admission_surface_root) is None
    ):
        raise IsolationBoundaryError(
            "semantic_admission_surface_root must be exact lowercase 64-hex"
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
        return {
            "pid": os.getpid(),
            "subject_generation": self._binding.subject_generation,
            "semantic_admission_surface_root": self._binding.semantic_admission_surface_root,
            "model_id": self._binding.model_id,
            "currentness_root": self._binding.currentness_root,
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
    """Start the current generation in a child and verify the child echoes that binding."""
    expected = bind_current_isolation_surface(
        subject_generation,
        semantic_admission_surface_root,
        model_id,
    )
    proxy = IsolatedObjectProxy(
        __name__,
        "IsolatedNativeAirLLMService",
        model_id,
        model_path,
        dict(model_allowlist),
        None if loader_source_allowlist is None else tuple(loader_source_allowlist),
        None if loader_package_source_allowlist is None else tuple(loader_package_source_allowlist),
        subject_generation,
        semantic_admission_surface_root,
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


__all__ = [
    "CurrentIsolationBinding",
    "IsolatedNativeAirLLMService",
    "bind_current_isolation_surface",
    "launch_isolated_native_airllm",
]
