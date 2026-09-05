"""Manifest-pinned compatibility for native AirLLM models with hard-false remote code.

AirLLM v4.0.0 contains internal calls that pass ``trust_remote_code=True`` even for
architectures now implemented natively by Transformers.  The strict wrapper correctly
rejects those calls, but that also makes the stock AutoModel path unusable for native
models such as GLM-5.3.

This opt-in wrapper narrows that compatibility seam without authorizing remote code:
only after exact model, loader-file, and package-source-manifest admission, known
Transformers loader boundaries are wrapped *inside* the strict hard-false membrane so
AirLLM's internal trust flag is rewritten to literal ``False``. Dynamic-module loading
remains denied. Caller-supplied widening requests remain errors.

Custom-code-required models still fail because their native ``False`` path fails and the
fallback ``True`` is rewritten to ``False`` rather than executed.

Claim ceiling: D0 software admission only.
"""
from __future__ import annotations

from contextlib import contextmanager
import inspect
import threading
from types import ModuleType
from typing import Any

try:
    from .airllm_manifest_pinned_wrapper import ManifestPinnedSecureAirLLMWrapper
    from .airllm_secure_wrapper import (
        LoaderSourceIntegrityError,
        ModelIntegrityError,
        RemoteCodeTrustError,
        UnsafeLoadOptionError,
        hard_false_remote_code_membrane,
        verify_loader_source,
    )
    from .airllm_source_manifest_guard import SourceTreeIntegrityError
except ImportError:
    from airllm_manifest_pinned_wrapper import ManifestPinnedSecureAirLLMWrapper
    from airllm_secure_wrapper import (
        LoaderSourceIntegrityError,
        ModelIntegrityError,
        RemoteCodeTrustError,
        UnsafeLoadOptionError,
        hard_false_remote_code_membrane,
        verify_loader_source,
    )
    from airllm_source_manifest_guard import SourceTreeIntegrityError

_NATIVE_COMPAT_BOUNDARIES = (
    ("AutoConfig", "from_pretrained"),
    ("AutoTokenizer", "from_pretrained"),
    ("AutoModel", "from_pretrained"),
    ("AutoModel", "from_config"),
    ("AutoModelForCausalLM", "from_pretrained"),
    ("AutoModelForCausalLM", "from_config"),
    ("AutoModelForImageTextToText", "from_pretrained"),
    ("AutoModelForImageTextToText", "from_config"),
    ("AutoModelForMultimodalLM", "from_pretrained"),
    ("AutoModelForMultimodalLM", "from_config"),
)
_COMPAT_LOCK = threading.RLock()


def _resolve_transformers_module(module: ModuleType | Any | None) -> Any:
    if module is not None:
        return module
    try:
        import transformers  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RemoteCodeTrustError("transformers is required for native AirLLM compatibility") from exc
    return transformers


def _rewrite_trust_false(original: Any, args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, Any]:
    rewritten = dict(kwargs)
    if "trust_remote_code" in rewritten:
        rewritten["trust_remote_code"] = False
        return rewritten
    try:
        signature = inspect.signature(original)
        bound = signature.bind_partial(*args, **rewritten)
    except (TypeError, ValueError):
        rewritten["trust_remote_code"] = False
        return rewritten
    if "trust_remote_code" in bound.arguments:
        # Positional trust_remote_code is unusual; refuse ambiguity rather than risk
        # leaving an earlier positional True in place while adding a duplicate kwarg.
        parameter = signature.parameters.get("trust_remote_code")
        if parameter is not None and parameter.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        ):
            ordered = list(signature.parameters)
            index = ordered.index("trust_remote_code")
            if len(args) > index:
                raise RemoteCodeTrustError(
                    "positional trust_remote_code is not admitted by native compatibility"
                )
        rewritten["trust_remote_code"] = False
    else:
        rewritten["trust_remote_code"] = False
    return rewritten


@contextmanager
def force_false_native_compat_membrane(transformers_module: ModuleType | Any | None = None):
    """Rewrite known AirLLM internal remote-code widening to literal False.

    This context must be entered only after exact AirLLM package-source admission. It is
    intentionally designed to sit inside ``hard_false_remote_code_membrane``: internal
    ``True`` first becomes ``False`` here, then the outer strict gate observes only the
    literal hard-false value.
    """
    module = _resolve_transformers_module(transformers_module)
    patches: list[tuple[Any, str, Any]] = []
    function_patches: list[tuple[Any, str, Any]] = []
    with _COMPAT_LOCK:
        try:
            for class_name, method_name in _NATIVE_COMPAT_BOUNDARIES:
                cls = getattr(module, class_name, None)
                if cls is None or not hasattr(cls, method_name):
                    continue
                raw_descriptor = inspect.getattr_static(cls, method_name)
                original = getattr(cls, method_name)

                def rewritten(
                    *args: Any,
                    __original: Any = original,
                    **kwargs: Any,
                ) -> Any:
                    safe_kwargs = _rewrite_trust_false(__original, args, kwargs)
                    return __original(*args, **safe_kwargs)

                setattr(cls, method_name, staticmethod(rewritten))
                patches.append((cls, method_name, raw_descriptor))

            dynamic_module = getattr(module, "dynamic_module_utils", None)
            if dynamic_module is not None and hasattr(dynamic_module, "get_class_from_dynamic_module"):
                original_dynamic = getattr(dynamic_module, "get_class_from_dynamic_module")

                def deny_dynamic_module(*args: Any, **kwargs: Any) -> Any:
                    raise RemoteCodeTrustError("dynamic Transformers module loading is not admitted")

                setattr(dynamic_module, "get_class_from_dynamic_module", deny_dynamic_module)
                function_patches.append((dynamic_module, "get_class_from_dynamic_module", original_dynamic))

            if not patches:
                raise RemoteCodeTrustError("no supported native Transformers loader boundaries were found")
            yield
        finally:
            for obj, name, original in reversed(function_patches):
                setattr(obj, name, original)
            for cls, method_name, raw_descriptor in reversed(patches):
                setattr(cls, method_name, raw_descriptor)


class ManifestPinnedNativeAirLLMWrapper(ManifestPinnedSecureAirLLMWrapper):
    """Strict manifest-pinned loader that permits only native Transformers execution."""

    def load(self, model_id: str, model_path: Any, *args: Any, **kwargs: Any) -> Any:
        requested_trust = kwargs.pop("trust_remote_code", False)
        if requested_trust is not False:
            raise RemoteCodeTrustError("caller trust_remote_code must be literal False")
        if kwargs.get("delete_original", False) is not False:
            raise UnsafeLoadOptionError(
                "delete_original=True is not admitted by the native manifest-pinned wrapper"
            )
        kwargs.setdefault("delete_original", False)

        first_model = self._base.verify(model_id, model_path)
        loader = self._base._resolve_loader()
        first_source = verify_loader_source(loader, self._base._loader_source_allowlist)
        first_package = self._verify_package_for_loader(loader)

        second_model = self._base.verify(model_id, model_path)
        second_source = verify_loader_source(loader, self._base._loader_source_allowlist)
        second_package = self._verify_package_for_loader(loader)
        if first_model != second_model:
            raise ModelIntegrityError("model identity changed before AirLLM invocation")
        if first_source != second_source:
            raise LoaderSourceIntegrityError("AirLLM loader source changed before invocation")
        if first_package != second_package:
            raise SourceTreeIntegrityError("AirLLM package source generation changed before invocation")

        # Outer strict membrane still defines the security ceiling. The inner compatibility
        # layer merely normalizes exactly-pinned AirLLM's known widening attempts to False.
        with hard_false_remote_code_membrane(self._base._transformers_module):
            final_package = self._verify_package_for_loader(loader)
            if final_package != second_package:
                raise SourceTreeIntegrityError(
                    "AirLLM package source generation changed at invocation boundary"
                )
            with force_false_native_compat_membrane(self._base._transformers_module):
                return loader.from_pretrained(second_model.path, *args, **kwargs)


__all__ = [
    "ManifestPinnedNativeAirLLMWrapper",
    "force_false_native_compat_membrane",
]
