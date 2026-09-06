from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import importlib
import json
import math
import os
import re
from typing import Any, Iterable, Mapping, Sequence

try:
    from .airllm_json_process_isolation import IsolatedSessionProxy, IsolationProtocolError
except ImportError:
    from airllm_json_process_isolation import IsolatedSessionProxy, IsolationProtocolError

_SCHEMA = "AURA-AIRLLM-GENERATION-BOUND-JSON-SERVICE-v1"
_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_DEFAULT_WRAPPER_SYMBOL = (
    "auraos.security.airllm_native_compat_wrapper",
    "ManifestPinnedNativeAirLLMWrapper",
)


def _canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise IsolationProtocolError("service values must be canonical JSON") from exc


def _exact_symbol(spec: Sequence[str]) -> tuple[str, str]:
    if not isinstance(spec, (list, tuple)) or len(spec) != 2 or not all(isinstance(v, str) and v and v.strip() == v for v in spec):
        raise IsolationProtocolError("symbol specs must contain exact module and public qualname strings")
    module_name, qualname = spec
    if any(not part or part.startswith("_") for part in qualname.split(".")):
        raise IsolationProtocolError("private or malformed symbol qualnames are not admitted")
    return module_name, qualname


def _resolve_symbol(spec: Sequence[str]) -> Any:
    module_name, qualname = _exact_symbol(spec)
    obj: Any = importlib.import_module(module_name)
    for part in qualname.split("."):
        obj = getattr(obj, part)
    if not callable(obj):
        raise IsolationProtocolError("resolved symbol is not callable")
    return obj


def _json_result(value: Any) -> Any:
    if hasattr(value, "tolist") and callable(value.tolist):
        value = value.tolist()
    if isinstance(value, dict):
        converted = {str(k): _json_result(v) for k, v in value.items()}
        if any(not isinstance(k, str) for k in value):
            raise IsolationProtocolError("result mappings must use string keys")
        _canonical_json(converted)
        return converted
    if isinstance(value, (list, tuple)):
        converted = [_json_result(v) for v in value]
        _canonical_json(converted)
        return converted
    if isinstance(value, float) and not math.isfinite(value):
        raise IsolationProtocolError("non-finite result values are not admitted")
    if value is None or isinstance(value, (str, int, float, bool)):
        _canonical_json(value)
        return value
    raise IsolationProtocolError(f"result type is not JSON-admissible: {type(value).__name__}")


@dataclass(frozen=True)
class GenerationBinding:
    subject_generation: str
    semantic_admission_surface_root: str
    model_id: str
    wrapper_module: str
    wrapper_qualname: str
    currentness_root: str


def bind_generation(subject_generation: str, semantic_admission_surface_root: str, model_id: str, wrapper_symbol: Sequence[str] = _DEFAULT_WRAPPER_SYMBOL) -> GenerationBinding:
    if not isinstance(subject_generation, str) or _HEX40.fullmatch(subject_generation) is None:
        raise IsolationProtocolError("subject_generation must be exact lowercase 40-hex")
    if not isinstance(semantic_admission_surface_root, str) or _HEX64.fullmatch(semantic_admission_surface_root) is None:
        raise IsolationProtocolError("semantic_admission_surface_root must be exact lowercase 64-hex")
    if not isinstance(model_id, str) or not model_id or model_id.strip() != model_id:
        raise IsolationProtocolError("model_id must be an exact non-empty string")
    wrapper_module, wrapper_qualname = _exact_symbol(wrapper_symbol)
    payload = {
        "schema": _SCHEMA,
        "subject_generation": subject_generation,
        "semantic_admission_surface_root": semantic_admission_surface_root,
        "model_id": model_id,
        "wrapper_module": wrapper_module,
        "wrapper_qualname": wrapper_qualname,
        "transport": "canonical-json-send-bytes-v1",
        "capabilities": ["generate_json", "status"],
    }
    return GenerationBinding(subject_generation, semantic_admission_surface_root, model_id, wrapper_module, wrapper_qualname, sha256(_canonical_json(payload)).hexdigest())


class GenerationBoundJsonSession:
    def __init__(self, *, model_id: str, model_path: str, model_allowlist: Mapping[str, Iterable[str]], loader_source_allowlist: Iterable[str] | None, loader_package_source_allowlist: Iterable[str] | None, subject_generation: str, semantic_admission_surface_root: str, wrapper_symbol: Sequence[str] = _DEFAULT_WRAPPER_SYMBOL, loader_package_required_paths: Sequence[str] | None = None, load_args: Sequence[Any] = (), load_kwargs: Mapping[str, Any] | None = None) -> None:
        self._binding = bind_generation(subject_generation, semantic_admission_surface_root, model_id, wrapper_symbol)
        wrapper_type = _resolve_symbol(wrapper_symbol)
        wrapper = wrapper_type(
            dict(model_allowlist),
            loader_source_allowlist=None if loader_source_allowlist is None else tuple(loader_source_allowlist),
            loader_package_source_allowlist=None if loader_package_source_allowlist is None else tuple(loader_package_source_allowlist),
            loader_package_required_paths=None if loader_package_required_paths is None else tuple(loader_package_required_paths),
        )
        kwargs = {} if load_kwargs is None else dict(load_kwargs)
        _canonical_json(list(load_args)); _canonical_json(kwargs)
        self._loaded = wrapper.load(model_id, model_path, *tuple(load_args), **kwargs)

    def status(self) -> dict[str, Any]:
        return {"schema": _SCHEMA, "pid": os.getpid(), "subject_generation": self._binding.subject_generation, "semantic_admission_surface_root": self._binding.semantic_admission_surface_root, "model_id": self._binding.model_id, "wrapper_module": self._binding.wrapper_module, "wrapper_qualname": self._binding.wrapper_qualname, "currentness_root": self._binding.currentness_root}

    def generate_json(self, request: Mapping[str, Any]) -> Any:
        if not isinstance(request, Mapping) or set(request) != {"args", "kwargs"}:
            raise IsolationProtocolError("generate_json request must contain exactly args and kwargs")
        args, kwargs = request["args"], request["kwargs"]
        if not isinstance(args, list) or not isinstance(kwargs, dict):
            raise IsolationProtocolError("generate_json args/kwargs must be JSON list/object")
        _canonical_json(args); _canonical_json(kwargs)
        method = getattr(self._loaded, "generate", None)
        if not callable(method):
            raise IsolationProtocolError("loaded object has no callable generate boundary")
        return _json_result(method(*args, **kwargs))

    def close(self) -> None:
        closer = getattr(self._loaded, "close", None)
        if callable(closer):
            closer()


def launch_generation_bound_json_service(*, model_id: str, model_path: str, model_allowlist: Mapping[str, Iterable[str]], loader_source_allowlist: Iterable[str] | None, loader_package_source_allowlist: Iterable[str] | None, subject_generation: str, semantic_admission_surface_root: str, wrapper_symbol: Sequence[str] = _DEFAULT_WRAPPER_SYMBOL, loader_package_required_paths: Sequence[str] | None = None, load_args: Sequence[Any] = (), load_kwargs: Mapping[str, Any] | None = None, timeout_seconds: float = 30.0) -> IsolatedSessionProxy:
    expected = bind_generation(subject_generation, semantic_admission_surface_root, model_id, wrapper_symbol)
    init_kwargs = {
        "model_id": model_id,
        "model_path": model_path,
        "model_allowlist": {k: list(v) for k, v in model_allowlist.items()},
        "loader_source_allowlist": None if loader_source_allowlist is None else list(loader_source_allowlist),
        "loader_package_source_allowlist": None if loader_package_source_allowlist is None else list(loader_package_source_allowlist),
        "subject_generation": subject_generation,
        "semantic_admission_surface_root": semantic_admission_surface_root,
        "wrapper_symbol": list(_exact_symbol(wrapper_symbol)),
        "loader_package_required_paths": None if loader_package_required_paths is None else list(loader_package_required_paths),
        "load_args": list(load_args),
        "load_kwargs": {} if load_kwargs is None else dict(load_kwargs),
    }
    _canonical_json(init_kwargs)
    proxy = IsolatedSessionProxy(factory_module=__name__, factory_qualname="GenerationBoundJsonSession", allowed_methods=("status", "generate_json"), init_kwargs=init_kwargs, startup_timeout=timeout_seconds, call_timeout=timeout_seconds)
    try:
        proxy.start(); status = proxy.call("status")
        if status.get("pid") != proxy.child_pid or status.get("schema") != _SCHEMA or status.get("subject_generation") != expected.subject_generation or status.get("semantic_admission_surface_root") != expected.semantic_admission_surface_root or status.get("model_id") != expected.model_id or status.get("wrapper_module") != expected.wrapper_module or status.get("wrapper_qualname") != expected.wrapper_qualname or status.get("currentness_root") != expected.currentness_root:
            raise IsolationProtocolError("child currentness/capability binding does not match requested surface")
        return proxy
    except BaseException:
        proxy.close(); raise


__all__ = ["GenerationBinding", "GenerationBoundJsonSession", "bind_generation", "launch_generation_bound_json_service"]
