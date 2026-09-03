"""Runtime HARD_FALSE membrane for the AWJ-032 AirLLM fixture path.

The static AirLLM source gate remains useful provenance and pre-import evidence,
but static AST inspection cannot prove that every future Python mutation form is
covered.  This module therefore enforces the security property again at the
actual Hugging Face Transformers loader boundaries reached by AirLLM.

The membrane is deliberately narrow:
- no AirLLM/model import is performed here;
- no network or checkpoint operation is performed here;
- caller attempts to pass ``trust_remote_code`` with any value other than the
  literal ``False`` are rejected before the wrapped loader runs;
- when the caller omits the flag, the membrane injects literal ``False``;
- no model path, token, credential, prompt, or other call argument is recorded;
- original descriptors are restored exactly when the membrane is released.

This is defense in depth over an exact remediated AirLLM source generation.  It
is not a general Python sandbox and does not prove that arbitrary imported code
is safe.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass
import hashlib
import json
from types import ModuleType
from typing import Any, Iterator

SCHEMA = "AuraAirLLMRuntimeHardFalseGuardV1"
POLICY = "TRUST_REMOTE_CODE_LITERAL_FALSE_ONLY"


class AirLLMRemoteCodeWideningRejected(RuntimeError):
    """Raised before a protected loader can execute with remote code enabled."""

    code = "AIRLLM_REMOTE_CODE_WIDENING_REJECTED"

    def __init__(self, boundary: str) -> None:
        super().__init__(f"{self.code}:{boundary}")
        self.boundary = boundary


class AirLLMRuntimeGuardError(RuntimeError):
    """Raised when the requested runtime boundary cannot be guarded exactly."""


@dataclass(frozen=True)
class BoundarySpec:
    owner_name: str
    method_name: str
    required: bool = True

    @property
    def boundary(self) -> str:
        return f"{self.owner_name}.{self.method_name}"


DEFAULT_BOUNDARIES: tuple[BoundarySpec, ...] = (
    BoundarySpec("AutoConfig", "from_pretrained"),
    BoundarySpec("AutoTokenizer", "from_pretrained"),
    BoundarySpec("AutoModelForCausalLM", "from_config"),
    BoundarySpec("AutoModel", "from_config"),
    # AirLLM probes these when the installed Transformers generation exposes
    # them.  Their absence is not a guard failure because AirLLM itself skips
    # unavailable factories.
    BoundarySpec("AutoModelForImageTextToText", "from_config", required=False),
    BoundarySpec("AutoModelForMultimodalLM", "from_config", required=False),
)


@dataclass(frozen=True)
class RuntimeHardFalseReceipt:
    schema: str
    policy: str
    installed_boundaries: tuple[str, ...]
    skipped_optional_boundaries: tuple[str, ...]
    protected_call_count: int
    rejected_widening_count: int
    active: bool
    claim_ceiling: str = "RUNTIME_LOADER_BOUNDARY_GUARD_NOT_GENERAL_PYTHON_SANDBOX"

    @property
    def receipt_digest(self) -> str:
        raw = json.dumps(
            asdict(self),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(b"AURA_AIRLLM_RUNTIME_HARD_FALSE_GUARD_V1\0" + raw).hexdigest()


@dataclass
class _Patch:
    owner: type
    method_name: str
    had_own_descriptor: bool
    original_descriptor: Any


class RuntimeHardFalseGuard:
    """Install and later restore exact classmethod guards on Transformers Auto APIs."""

    def __init__(
        self,
        transformers_module: ModuleType | Any,
        *,
        boundaries: tuple[BoundarySpec, ...] = DEFAULT_BOUNDARIES,
    ) -> None:
        self._transformers = transformers_module
        self._boundaries = boundaries
        self._patches: list[_Patch] = []
        self._installed_boundaries: list[str] = []
        self._skipped_optional: list[str] = []
        self._protected_call_count = 0
        self._rejected_widening_count = 0
        self._active = False

    def _guarded_classmethod(self, original_bound: Any, boundary: str) -> classmethod:
        guard = self

        @classmethod
        def guarded(cls: type, *args: Any, **kwargs: Any) -> Any:
            del cls  # the saved original is already bound to its real owner
            guard._protected_call_count += 1
            if "trust_remote_code" in kwargs and kwargs["trust_remote_code"] is not False:
                guard._rejected_widening_count += 1
                raise AirLLMRemoteCodeWideningRejected(boundary)
            kwargs["trust_remote_code"] = False
            return original_bound(*args, **kwargs)

        guarded.__name__ = getattr(original_bound, "__name__", "guarded")
        guarded.__qualname__ = f"RuntimeHardFalseGuard.{boundary}"
        return classmethod(guarded)

    def install(self) -> "RuntimeHardFalseGuard":
        if self._active:
            raise AirLLMRuntimeGuardError("AIRLLM_RUNTIME_HARD_FALSE_GUARD_ALREADY_ACTIVE")

        try:
            for spec in self._boundaries:
                owner = getattr(self._transformers, spec.owner_name, None)
                if owner is None:
                    if spec.required:
                        raise AirLLMRuntimeGuardError(
                            f"AIRLLM_RUNTIME_BOUNDARY_OWNER_MISSING:{spec.owner_name}"
                        )
                    self._skipped_optional.append(spec.boundary)
                    continue

                original_bound = getattr(owner, spec.method_name, None)
                if original_bound is None or not callable(original_bound):
                    if spec.required:
                        raise AirLLMRuntimeGuardError(
                            f"AIRLLM_RUNTIME_BOUNDARY_METHOD_MISSING:{spec.boundary}"
                        )
                    self._skipped_optional.append(spec.boundary)
                    continue

                had_own = spec.method_name in owner.__dict__
                original_descriptor = owner.__dict__.get(spec.method_name)
                self._patches.append(
                    _Patch(
                        owner=owner,
                        method_name=spec.method_name,
                        had_own_descriptor=had_own,
                        original_descriptor=original_descriptor,
                    )
                )
                setattr(
                    owner,
                    spec.method_name,
                    self._guarded_classmethod(original_bound, spec.boundary),
                )
                self._installed_boundaries.append(spec.boundary)
        except Exception:
            self._restore_patches()
            raise

        self._active = True
        return self

    def _restore_patches(self) -> None:
        for patch in reversed(self._patches):
            if patch.had_own_descriptor:
                setattr(patch.owner, patch.method_name, patch.original_descriptor)
            else:
                try:
                    delattr(patch.owner, patch.method_name)
                except AttributeError:
                    pass
        self._patches.clear()
        self._installed_boundaries.clear()
        self._skipped_optional.clear()
        self._active = False

    def restore(self) -> None:
        self._restore_patches()

    def receipt(self) -> RuntimeHardFalseReceipt:
        return RuntimeHardFalseReceipt(
            schema=SCHEMA,
            policy=POLICY,
            installed_boundaries=tuple(self._installed_boundaries),
            skipped_optional_boundaries=tuple(self._skipped_optional),
            protected_call_count=self._protected_call_count,
            rejected_widening_count=self._rejected_widening_count,
            active=self._active,
        )

    def __enter__(self) -> "RuntimeHardFalseGuard":
        return self.install()

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        del exc_type, exc, tb
        self.restore()


def install_transformers_hard_false_guard(
    transformers_module: ModuleType | Any | None = None,
    *,
    boundaries: tuple[BoundarySpec, ...] = DEFAULT_BOUNDARIES,
) -> RuntimeHardFalseGuard:
    """Install the guard before importing/constructing AirLLM model objects."""
    if transformers_module is None:
        import transformers as transformers_module  # type: ignore[no-redef]
    return RuntimeHardFalseGuard(
        transformers_module,
        boundaries=boundaries,
    ).install()


@contextmanager
def transformers_hard_false_guard(
    transformers_module: ModuleType | Any | None = None,
    *,
    boundaries: tuple[BoundarySpec, ...] = DEFAULT_BOUNDARIES,
) -> Iterator[RuntimeHardFalseGuard]:
    guard = RuntimeHardFalseGuard(
        transformers_module if transformers_module is not None else _import_transformers(),
        boundaries=boundaries,
    )
    guard.install()
    try:
        yield guard
    finally:
        guard.restore()


def _import_transformers() -> ModuleType:
    import transformers

    return transformers
