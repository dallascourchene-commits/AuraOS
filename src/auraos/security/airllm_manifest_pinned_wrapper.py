"""Strict AirLLM entrypoint binding model, loader file, and package-source identity.

This composes the existing SecureAirLLMWrapper with the exact package-source manifest
primitive.  It preserves the older wrapper for compatibility, while making transitive
source provenance an explicit hard requirement for callers that opt into this stricter
entrypoint.

Claim ceiling: D0 software admission only.  Rechecks narrow the mutation window but do
not create filesystem immutability; production execution still needs an immutable or
sandboxed source tree if the threat model includes concurrent local writers.
"""
from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any, Iterable, Mapping, Sequence

try:  # package import
    from .airllm_secure_wrapper import (
        LoaderSourceIntegrityError,
        ModelIntegrityError,
        RemoteCodeTrustError,
        SecureAirLLMWrapper,
        UnsafeLoadOptionError,
        hard_false_remote_code_membrane,
        verify_loader_source,
    )
    from .airllm_source_manifest_guard import (
        SourceTreeIntegrityError,
        VerifiedSourceManifest,
        normalize_manifest_allowlist,
        verify_source_manifest,
    )
except ImportError:  # direct stdlib-only test execution from this directory
    from airllm_secure_wrapper import (
        LoaderSourceIntegrityError,
        ModelIntegrityError,
        RemoteCodeTrustError,
        SecureAirLLMWrapper,
        UnsafeLoadOptionError,
        hard_false_remote_code_membrane,
        verify_loader_source,
    )
    from airllm_source_manifest_guard import (
        SourceTreeIntegrityError,
        VerifiedSourceManifest,
        normalize_manifest_allowlist,
        verify_source_manifest,
    )


class ManifestPinnedSecureAirLLMWrapper:
    """Fail closed unless the full admitted AirLLM package generation is exact."""

    def __init__(
        self,
        model_allowlist: Mapping[str, Iterable[str]],
        *,
        loader_source_allowlist: Iterable[str] | None,
        loader_package_source_allowlist: Iterable[str] | None,
        loader_package_required_paths: Sequence[str] | None = None,
        loader: Any | None = None,
        transformers_module: ModuleType | Any | None = None,
    ) -> None:
        self._base = SecureAirLLMWrapper(
            model_allowlist,
            loader_source_allowlist=loader_source_allowlist,
            loader=loader,
            transformers_module=transformers_module,
        )
        self._package_allowlist = normalize_manifest_allowlist(
            loader_package_source_allowlist
        )
        self._required_paths = (
            None if loader_package_required_paths is None
            else tuple(loader_package_required_paths)
        )

    def verify(self, model_id: str, model_path: str | Path):
        return self._base.verify(model_id, model_path)

    def _verify_package_for_loader(self, loader: Any) -> VerifiedSourceManifest:
        # The exact loader source is separately pinned by the base wrapper.  Its parent
        # directory is therefore the package root whose transitive source generation is
        # admitted here; callers cannot point the manifest guard at an unrelated clean tree.
        verified_source = verify_loader_source(
            loader, self._base._loader_source_allowlist
        )
        package_root = Path(verified_source.path).parent
        return verify_source_manifest(
            package_root,
            self._package_allowlist,
            required_paths=self._required_paths,
        )

    def load(
        self,
        model_id: str,
        model_path: str | Path,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        requested_trust = kwargs.pop("trust_remote_code", False)
        if requested_trust is not False:
            raise RemoteCodeTrustError("trust_remote_code must be literal False")
        if kwargs.get("delete_original", False) is not False:
            raise UnsafeLoadOptionError(
                "delete_original=True is not admitted by the manifest-pinned wrapper"
            )
        kwargs.setdefault("delete_original", False)

        first_model = self._base.verify(model_id, model_path)
        loader = self._base._resolve_loader()
        first_source = verify_loader_source(
            loader, self._base._loader_source_allowlist
        )
        first_package = self._verify_package_for_loader(loader)

        # Revalidate all three identities after import/resolution work.
        second_model = self._base.verify(model_id, model_path)
        second_source = verify_loader_source(
            loader, self._base._loader_source_allowlist
        )
        second_package = self._verify_package_for_loader(loader)
        if first_model != second_model:
            raise ModelIntegrityError("model identity changed before AirLLM invocation")
        if first_source != second_source:
            raise LoaderSourceIntegrityError(
                "AirLLM loader source changed before invocation"
            )
        if first_package != second_package:
            raise SourceTreeIntegrityError(
                "AirLLM package source generation changed before invocation"
            )

        # One final package recheck occurs inside the hard-false membrane, immediately
        # before the loader call.  This minimizes but does not claim to eliminate a
        # local-filesystem TOCTOU window.
        with hard_false_remote_code_membrane(self._base._transformers_module):
            final_package = self._verify_package_for_loader(loader)
            if final_package != second_package:
                raise SourceTreeIntegrityError(
                    "AirLLM package source generation changed at invocation boundary"
                )
            return loader.from_pretrained(second_model.path, *args, **kwargs)


__all__ = ["ManifestPinnedSecureAirLLMWrapper"]
