"""Policy-bound backend-neutral inference gateway for Aura.

This is a thin membrane around existing Aura owners. It does not read repository
source for model context, choose work decomposition, grant provider permission,
or mutate production state. Callers supply a bounded context compiler and
backend adapters; the gateway binds an exact model policy before any backend can
run and emits deterministic nonauthority receipts.

P0 intentionally executes only deterministic/no-model and local-model classes.
External escalation remains owned by the existing external-session/provider plane.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
import math
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Mapping, Protocol

POLICY_SCHEMA = "AURA_MODEL_POLICY_V1"
REQUEST_SCHEMA = "AURA_LOCAL_INFERENCE_REQUEST_V1"
CONTEXT_SCHEMA = "AURA_LOCAL_INFERENCE_CONTEXT_V1"
CAPABILITY_SCHEMA = "AURA_LOCAL_INFERENCE_BACKEND_CAPABILITY_V1"
RECEIPT_SCHEMA = "AURA_LOCAL_INFERENCE_RECEIPT_V1"

SUPPORTED_POLICY_BACKENDS = {"no_model", "local_model", "external_model"}
P0_EXECUTABLE_BACKENDS = frozenset({"no_model", "local_model"})
BACKEND_CLASS_BY_POLICY_VALUE = {
    "no_model": "no_model",
    "local_model": "local_model",
    "external_model": "external_model",
}
FORBIDDEN_CONTEXT_CLASSES = frozenset({"secrets", "hidden_reasoning", "unrelated_sessions"})
NONAUTHORITY_EFFECT_STATE = "NO_PRODUCTION_MUTATION"


class PolicyResolutionError(ValueError):
    """Raised when an exact model policy cannot be admitted."""


class StalePolicyError(PolicyResolutionError):
    """Raised when an expected policy digest no longer matches."""


def _json_snapshot(value: Any, field_name: str = "identity") -> Any:
    """Deep-copy identity-bearing values into immutable, finite JSON data."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{field_name}_nonfinite")
        return value
    if isinstance(value, Mapping):
        frozen: dict[str, Any] = {}
        for key, child in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{field_name}_mapping_key_must_be_string")
            frozen[key] = _json_snapshot(child, f"{field_name}.{key}")
        return MappingProxyType(frozen)
    if isinstance(value, (list, tuple)):
        return tuple(_json_snapshot(child, f"{field_name}[]") for child in value)
    raise ValueError(f"{field_name}_unsupported_type:{type(value).__name__}")


def _json_plain(value: Any) -> Any:
    """Convert an admitted immutable JSON snapshot back to plain JSON values."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("identity_nonfinite")
        return value
    if isinstance(value, Mapping):
        return {key: _json_plain(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_plain(child) for child in value]
    raise ValueError(f"identity_unsupported_type:{type(value).__name__}")


def _canonical_json(value: Any) -> str:
    return json.dumps(
        _json_plain(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_json(value: Any) -> str:
    return _sha256_bytes(_canonical_json(value).encode("utf-8"))


def _require_nonempty_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name}_required")
    return value


def _require_string_tuple(values: Any, field_name: str) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)):
        raise ValueError(f"{field_name}_must_be_sequence")
    normalized = tuple(_require_nonempty_text(value, field_name) for value in values)
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"{field_name}_duplicates_forbidden")
    return normalized


def _safe_text(value: Any) -> str | None:
    return value if isinstance(value, str) else None


@dataclass(frozen=True)
class PolicyDecision:
    policy_ref: str
    policy_blob_digest: str
    allowed_backend_classes: tuple[str, ...]
    default: str
    fallback: str
    external_allowed: bool
    max_calls: int
    escalation_requirements: tuple[str, ...]
    currentness: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ModelPolicyResolver:
    """Resolve one exact repository-owned model policy and fail closed."""

    _required_keys = frozenset(
        {
            "schema_version",
            "component_id",
            "kind",
            "default",
            "fallback",
            "external_allowed",
            "maximum_model_calls",
            "escalation_requires",
        }
    )

    def __init__(self, repo_root: str | Path = ".") -> None:
        self.repo_root = Path(repo_root).resolve()
        self.policy_root = (self.repo_root / ".aura" / "model_policies").resolve()

    def resolve(self, policy_ref: str, *, expected_sha256: str | None = None) -> PolicyDecision:
        normalized_ref = self._validate_policy_ref(policy_ref)
        declared_path = self.repo_root / normalized_ref
        self._reject_symlink_path(declared_path)
        path = declared_path.resolve()
        try:
            path.relative_to(self.policy_root)
        except ValueError as exc:
            raise PolicyResolutionError("policy_ref_outside_policy_owner") from exc
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise PolicyResolutionError("policy_unreadable") from exc
        digest = _sha256_bytes(raw)
        if expected_sha256 is not None and digest != str(expected_sha256):
            raise StalePolicyError("policy_digest_mismatch")
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PolicyResolutionError("policy_malformed_json") from exc
        decision = self._validate_payload(payload, normalized_ref, digest)
        if expected_sha256 is None:
            return decision
        return PolicyDecision(**{**decision.to_dict(), "currentness": "EXACT_DIGEST_MATCH"})

    def _reject_symlink_path(self, declared_path: Path) -> None:
        try:
            relative = declared_path.relative_to(self.repo_root)
        except ValueError as exc:
            raise PolicyResolutionError("policy_ref_outside_repository") from exc
        cursor = self.repo_root
        for part in relative.parts:
            cursor = cursor / part
            if cursor.is_symlink():
                raise PolicyResolutionError("policy_symlink_forbidden")

    @classmethod
    def _validate_policy_ref(cls, policy_ref: str) -> str:
        ref = _require_nonempty_text(policy_ref, "policy_ref").replace("\\", "/")
        path = Path(ref)
        if path.is_absolute() or ".." in path.parts:
            raise PolicyResolutionError("policy_ref_invalid")
        parts = path.parts
        if len(parts) < 3 or parts[0] != ".aura" or parts[1] != "model_policies":
            raise PolicyResolutionError("policy_ref_wrong_owner")
        return path.as_posix()

    @classmethod
    def _validate_payload(cls, payload: Any, policy_ref: str, digest: str) -> PolicyDecision:
        if not isinstance(payload, dict):
            raise PolicyResolutionError("policy_must_be_object")
        keys = frozenset(payload)
        missing = cls._required_keys - keys
        unknown = keys - cls._required_keys
        if missing:
            raise PolicyResolutionError(f"policy_missing_fields:{','.join(sorted(missing))}")
        if unknown:
            raise PolicyResolutionError(f"policy_unknown_fields:{','.join(sorted(unknown))}")
        if payload["schema_version"] != POLICY_SCHEMA:
            raise PolicyResolutionError("policy_schema_unsupported")
        if payload["kind"] != "model_policy":
            raise PolicyResolutionError("policy_kind_invalid")
        _require_nonempty_text(payload["component_id"], "component_id")
        default = _require_nonempty_text(payload["default"], "default")
        fallback = _require_nonempty_text(payload["fallback"], "fallback")
        if default not in SUPPORTED_POLICY_BACKENDS or fallback not in SUPPORTED_POLICY_BACKENDS:
            raise PolicyResolutionError("policy_backend_class_unsupported")
        external_allowed = payload["external_allowed"]
        if not isinstance(external_allowed, bool):
            raise PolicyResolutionError("external_allowed_must_be_bool")
        max_calls = payload["maximum_model_calls"]
        if isinstance(max_calls, bool) or not isinstance(max_calls, int) or max_calls < 0:
            raise PolicyResolutionError("maximum_model_calls_invalid")
        requirements = _require_string_tuple(payload["escalation_requires"], "escalation_requires")
        backend_values = (default, fallback)
        if "external_model" in backend_values and not external_allowed:
            raise PolicyResolutionError("external_backend_forbidden_by_policy")

        # P0 records policy external eligibility but never executes that class here.
        allowed: list[str] = []
        for value in backend_values:
            backend_class = BACKEND_CLASS_BY_POLICY_VALUE[value]
            if backend_class in P0_EXECUTABLE_BACKENDS and backend_class not in allowed:
                allowed.append(backend_class)

        return PolicyDecision(
            policy_ref=policy_ref,
            policy_blob_digest=digest,
            allowed_backend_classes=tuple(allowed),
            default=default,
            fallback=fallback,
            external_allowed=external_allowed,
            max_calls=max_calls,
            escalation_requirements=requirements,
            currentness="OBSERVED_AT_RESOLUTION",
        )


@dataclass(frozen=True)
class InferenceRequestV1:
    request_id: str
    objective: str
    model_policy_ref: str
    expected_policy_sha256: str | None = None
    bound_context_digest: str | None = None
    backend_hint: str | None = None
    coordinate_hint: str | None = None
    required_evidence: tuple[str, ...] = ("source", "currentness", "authority", "privacy")
    required_privacy_exclusions: tuple[str, ...] = ()
    escalation_evidence: tuple[str, ...] = ()

    def protected_dict(self) -> dict[str, Any]:
        return {
            "schema_id": REQUEST_SCHEMA,
            "schema_version": 1,
            "request_id": self.request_id,
            "objective": self.objective,
            "model_policy_ref": self.model_policy_ref,
            "expected_policy_sha256": self.expected_policy_sha256,
            "bound_context_digest": self.bound_context_digest,
            "backend_hint": self.backend_hint,
            "coordinate_hint": self.coordinate_hint,
            "required_evidence": list(self.required_evidence),
            "required_privacy_exclusions": list(self.required_privacy_exclusions),
            "escalation_evidence": list(self.escalation_evidence),
        }

    @property
    def digest(self) -> str:
        return _sha256_json(self.protected_dict())


@dataclass(frozen=True)
class CompiledContextV1:
    source_refs: tuple[str, ...]
    currentness_refs: tuple[str, ...]
    authority_refs: tuple[str, ...]
    privacy_refs: tuple[str, ...]
    reopen_refs: tuple[str, ...]
    privacy_exclusions: tuple[str, ...]
    payload: Mapping[str, Any] = field(default_factory=dict)

    def protected_dict(self) -> dict[str, Any]:
        return {
            "schema_id": CONTEXT_SCHEMA,
            "schema_version": 1,
            "source_refs": list(self.source_refs),
            "currentness_refs": list(self.currentness_refs),
            "authority_refs": list(self.authority_refs),
            "privacy_refs": list(self.privacy_refs),
            "reopen_refs": list(self.reopen_refs),
            "privacy_exclusions": list(self.privacy_exclusions),
            "payload": _json_plain(self.payload),
        }

    @property
    def digest(self) -> str:
        return _sha256_json(self.protected_dict())


@dataclass(frozen=True)
class BackendCapabilityV1:
    backend_id: str
    backend_class: str
    available: bool
    network_required: bool = False
    artifact_ref: str | None = None
    resource_state: Mapping[str, Any] = field(default_factory=dict)

    def protected_dict(self) -> dict[str, Any]:
        return {
            "schema_id": CAPABILITY_SCHEMA,
            "schema_version": 1,
            "backend_id": self.backend_id,
            "backend_class": self.backend_class,
            "available": self.available,
            "network_required": self.network_required,
            "artifact_ref": self.artifact_ref,
            "resource_state": _json_plain(self.resource_state),
        }

    @property
    def digest(self) -> str:
        return _sha256_json(self.protected_dict())


@dataclass(frozen=True)
class BackendResultV1:
    satisfied: bool
    output: str = ""
    uncertainty: tuple[str, ...] = ()
    counterevidence: tuple[str, ...] = ()
    measurements: Mapping[str, Any] = field(default_factory=dict)
    measurement_class: str = "UNKNOWN"


class BackendAdapter(Protocol):
    capability: BackendCapabilityV1
    counts_as_model_call: bool

    def invoke(self, request: InferenceRequestV1, context: CompiledContextV1) -> BackendResultV1:
        ...


class DeterministicBackend:
    counts_as_model_call = False

    def __init__(
        self,
        callback: Callable[[InferenceRequestV1, CompiledContextV1], str | None],
        *,
        backend_id: str = "deterministic",
    ) -> None:
        self.callback = callback
        self.capability = BackendCapabilityV1(
            backend_id=backend_id,
            backend_class="no_model",
            available=True,
            resource_state={"class": "deterministic", "state": "AVAILABLE"},
        )

    def invoke(self, request: InferenceRequestV1, context: CompiledContextV1) -> BackendResultV1:
        output = self.callback(request, context)
        if output is None:
            return BackendResultV1(
                satisfied=False,
                uncertainty=("deterministic_path_insufficient",),
                measurement_class="MEASURED_LOCAL",
            )
        return BackendResultV1(satisfied=True, output=str(output), measurement_class="MEASURED_LOCAL")


class FakeLocalBackend:
    """Test-only local-model class adapter; never installs or calls a real model."""

    counts_as_model_call = True

    def __init__(
        self,
        callback: Callable[[InferenceRequestV1, CompiledContextV1], str],
        *,
        backend_id: str = "fake-local",
        available: bool = True,
    ) -> None:
        self.callback = callback
        self.call_count = 0
        self.capability = BackendCapabilityV1(
            backend_id=backend_id,
            backend_class="local_model",
            available=bool(available),
            artifact_ref="fake://local-test-backend",
            resource_state={"cpu": "UNKNOWN", "ram": "UNKNOWN", "gpu": "UNKNOWN", "vram": "UNKNOWN"},
        )

    def invoke(self, request: InferenceRequestV1, context: CompiledContextV1) -> BackendResultV1:
        self.call_count += 1
        return BackendResultV1(
            satisfied=True,
            output=str(self.callback(request, context)),
            measurements={"model_calls": 1},
            measurement_class="MEASURED_FAKE",
        )


class ExternalBackendForTest:
    """Negative-test adapter proving external labels cannot bypass the P0 gateway."""

    counts_as_model_call = True

    def __init__(self, *, backend_id: str = "external-test") -> None:
        self.call_count = 0
        self.capability = BackendCapabilityV1(
            backend_id=backend_id,
            backend_class="external_model",
            available=True,
            network_required=True,
            artifact_ref="test://external",
            resource_state={"network": "AVAILABLE"},
        )

    def invoke(self, request: InferenceRequestV1, context: CompiledContextV1) -> BackendResultV1:
        self.call_count += 1
        return BackendResultV1(satisfied=True, output="external", measurement_class="TEST_ONLY")


def request_from_route_capsule(
    route_capsule: Mapping[str, Any],
    *,
    request_id: str,
    objective: str,
    **kwargs: Any,
) -> InferenceRequestV1:
    policy_ref = route_capsule.get("model_policy_ref")
    if not isinstance(policy_ref, str) or not policy_ref:
        raise ValueError("route_capsule_model_policy_ref_required")
    return InferenceRequestV1(
        request_id=_require_nonempty_text(request_id, "request_id"),
        objective=_require_nonempty_text(objective, "objective"),
        model_policy_ref=policy_ref,
        **kwargs,
    )


def _snapshot_context(context: CompiledContextV1) -> CompiledContextV1:
    if not isinstance(context, CompiledContextV1):
        raise ValueError("context_schema_invalid")
    return CompiledContextV1(
        source_refs=_require_string_tuple(context.source_refs, "source_refs"),
        currentness_refs=_require_string_tuple(context.currentness_refs, "currentness_refs"),
        authority_refs=_require_string_tuple(context.authority_refs, "authority_refs"),
        privacy_refs=_require_string_tuple(context.privacy_refs, "privacy_refs"),
        reopen_refs=_require_string_tuple(context.reopen_refs, "reopen_refs"),
        privacy_exclusions=_require_string_tuple(context.privacy_exclusions, "privacy_exclusions"),
        payload=_json_snapshot(context.payload, "context_payload"),
    )


def _snapshot_capability(capability: BackendCapabilityV1) -> BackendCapabilityV1:
    if not isinstance(capability, BackendCapabilityV1):
        raise ValueError("backend_capability_schema_invalid")
    backend_id = _require_nonempty_text(capability.backend_id, "backend_id")
    backend_class = _require_nonempty_text(capability.backend_class, "backend_class")
    if backend_class not in SUPPORTED_POLICY_BACKENDS:
        raise ValueError("backend_capability_class_unknown")
    if not isinstance(capability.available, bool) or not isinstance(capability.network_required, bool):
        raise ValueError("backend_capability_boolean_invalid")
    if capability.artifact_ref is not None and not isinstance(capability.artifact_ref, str):
        raise ValueError("backend_artifact_ref_invalid")
    return BackendCapabilityV1(
        backend_id=backend_id,
        backend_class=backend_class,
        available=capability.available,
        network_required=capability.network_required,
        artifact_ref=capability.artifact_ref,
        resource_state=_json_snapshot(capability.resource_state, "backend_resource_state"),
    )


def _snapshot_result(result: Any) -> BackendResultV1:
    if not isinstance(result, BackendResultV1):
        raise ValueError("backend_result_schema_invalid")
    if not isinstance(result.satisfied, bool):
        raise ValueError("backend_result_satisfied_invalid")
    if not isinstance(result.output, str):
        raise ValueError("backend_result_output_invalid")
    uncertainty = _require_string_tuple(result.uncertainty, "backend_result_uncertainty")
    counterevidence = _require_string_tuple(result.counterevidence, "backend_result_counterevidence")
    measurement_class = _require_nonempty_text(result.measurement_class, "measurement_class")
    measurements = _json_snapshot(result.measurements, "backend_result_measurements")
    if not isinstance(measurements, Mapping):
        raise ValueError("backend_result_measurements_must_be_mapping")
    return BackendResultV1(
        satisfied=result.satisfied,
        output=result.output,
        uncertainty=uncertainty,
        counterevidence=counterevidence,
        measurements=measurements,
        measurement_class=measurement_class,
    )


class LocalInferenceGateway:
    """Bind policy -> bounded context -> eligible P0 backend -> nonauthority receipt."""

    def __init__(
        self,
        *,
        policy_resolver: ModelPolicyResolver,
        context_compiler: Callable[[InferenceRequestV1], CompiledContextV1],
        backends: tuple[BackendAdapter, ...] | list[BackendAdapter],
    ) -> None:
        self.policy_resolver = policy_resolver
        self.context_compiler = context_compiler
        self.backends = tuple(backends)

    def run(self, request: InferenceRequestV1) -> dict[str, Any]:
        try:
            self._validate_request(request)
            policy = self.policy_resolver.resolve(
                request.model_policy_ref,
                expected_sha256=request.expected_policy_sha256,
            )
        except StalePolicyError:
            return self._blocked_receipt(request, "BLOCKED_STALE_POLICY")
        except (PolicyResolutionError, ValueError) as exc:
            return self._blocked_receipt(request, "BLOCKED_POLICY_INVALID", details={"error": str(exc)})

        if request.backend_hint == "external_model":
            status = (
                "BLOCKED_POLICY_EXTERNAL_FORBIDDEN"
                if not policy.external_allowed
                else "BLOCKED_EXTERNAL_DELEGATION_REQUIRED"
            )
            return self._blocked_receipt(request, status, policy=policy)

        try:
            compiled = self.context_compiler(request)
            context = _snapshot_context(compiled)
        except Exception as exc:  # context-owner failure never authorizes broader hydration
            return self._blocked_receipt(
                request,
                "BLOCKED_CONTEXT_UNAVAILABLE",
                policy=policy,
                details={"error_type": type(exc).__name__, "error": str(exc)},
            )

        context_problem = self._context_problem(request, context)
        if context_problem:
            return self._blocked_receipt(request, context_problem, policy=policy, context=context)

        attempts: list[dict[str, Any]] = []
        aggregate_uncertainty: list[str] = []
        aggregate_counterevidence: list[str] = []
        model_calls = 0

        for backend_class in self._ordered_backend_classes(policy):
            adapter = self._find_backend(backend_class)
            if adapter is None:
                attempts.append(
                    {"backend_class": backend_class, "status": "UNAVAILABLE", "capability_digest": None}
                )
                continue
            try:
                capability = _snapshot_capability(adapter.capability)
            except Exception as exc:
                attempts.append(
                    {
                        "backend_class": backend_class,
                        "status": "BLOCKED_CAPABILITY_INVALID",
                        "error_type": type(exc).__name__,
                        "capability_digest": None,
                    }
                )
                continue

            if capability.backend_class != backend_class:
                attempts.append(
                    {
                        "backend_class": backend_class,
                        "backend_id": capability.backend_id,
                        "status": "BLOCKED_CAPABILITY_CLASS_MISMATCH",
                        "capability_digest": capability.digest,
                    }
                )
                continue
            if not capability.available:
                attempts.append(
                    {
                        "backend_class": backend_class,
                        "backend_id": capability.backend_id,
                        "status": "UNAVAILABLE",
                        "capability_digest": capability.digest,
                    }
                )
                continue
            if capability.network_required:
                attempts.append(
                    {
                        "backend_class": backend_class,
                        "backend_id": capability.backend_id,
                        "status": "BLOCKED_P0_BACKEND_REQUIRES_NETWORK",
                        "capability_digest": capability.digest,
                    }
                )
                continue

            # Model-call accounting is authority-derived from the admitted backend class,
            # never from adapter-controlled metadata.
            counts_as_model_call = backend_class == "local_model"
            if counts_as_model_call:
                if model_calls >= policy.max_calls:
                    attempts.append(
                        {
                            "backend_class": backend_class,
                            "backend_id": capability.backend_id,
                            "status": "BLOCKED_MODEL_CALL_BUDGET",
                            "capability_digest": capability.digest,
                        }
                    )
                    continue
                model_calls += 1

            try:
                result = _snapshot_result(adapter.invoke(request, context))
            except Exception as exc:
                attempts.append(
                    {
                        "backend_class": backend_class,
                        "backend_id": capability.backend_id,
                        "status": "FAILED_TYPED",
                        "error_type": type(exc).__name__,
                        "capability_digest": capability.digest,
                    }
                )
                continue

            aggregate_uncertainty.extend(result.uncertainty)
            aggregate_counterevidence.extend(result.counterevidence)
            attempts.append(
                {
                    "backend_class": backend_class,
                    "backend_id": capability.backend_id,
                    "status": "SATISFIED" if result.satisfied else "INSUFFICIENT",
                    "capability_digest": capability.digest,
                    "measurement_class": result.measurement_class,
                    "measurements": _json_plain(result.measurements),
                    "uncertainty": list(result.uncertainty),
                    "counterevidence": list(result.counterevidence),
                }
            )
            if result.satisfied:
                return self._success_receipt(
                    request=request,
                    policy=policy,
                    context=context,
                    capability=capability,
                    result=result,
                    attempts=attempts,
                    model_calls=model_calls,
                )

        return self._blocked_receipt(
            request,
            "BLOCKED_NO_ELIGIBLE_BACKEND",
            policy=policy,
            context=context,
            details={"attempts": attempts},
            model_calls=model_calls,
            uncertainty=aggregate_uncertainty,
            counterevidence=aggregate_counterevidence,
        )

    @staticmethod
    def _validate_request(request: InferenceRequestV1) -> None:
        if not isinstance(request, InferenceRequestV1):
            raise ValueError("request_schema_invalid")
        _require_nonempty_text(request.request_id, "request_id")
        _require_nonempty_text(request.objective, "objective")
        _require_nonempty_text(request.model_policy_ref, "model_policy_ref")
        _require_string_tuple(request.required_evidence, "required_evidence")
        _require_string_tuple(request.required_privacy_exclusions, "required_privacy_exclusions")
        _require_string_tuple(request.escalation_evidence, "escalation_evidence")
        if not set(request.required_evidence) <= {"source", "currentness", "authority", "privacy"}:
            raise ValueError("required_evidence_unknown")
        if request.backend_hint is not None and request.backend_hint not in SUPPORTED_POLICY_BACKENDS:
            raise ValueError("backend_hint_unknown")
        for field_name in (
            "expected_policy_sha256",
            "bound_context_digest",
            "coordinate_hint",
        ):
            value = getattr(request, field_name)
            if value is not None and not isinstance(value, str):
                raise ValueError(f"{field_name}_invalid")

    @staticmethod
    def _context_problem(request: InferenceRequestV1, context: CompiledContextV1) -> str | None:
        evidence = {
            "source": context.source_refs,
            "currentness": context.currentness_refs,
            "authority": context.authority_refs,
            "privacy": context.privacy_refs,
        }
        for key in request.required_evidence:
            if not evidence[key]:
                return "BLOCKED_REQUIRED_EVIDENCE_UNRESOLVED"
        if request.bound_context_digest is not None and request.bound_context_digest != context.digest:
            return "BLOCKED_CONTEXT_DIGEST_MISMATCH"

        # The baseline privacy proof is mandatory even when the caller asks for none.
        if not FORBIDDEN_CONTEXT_CLASSES <= set(context.privacy_exclusions):
            return "BLOCKED_PRIVACY_EXCLUSIONS_INCOMPLETE"
        if not set(request.required_privacy_exclusions) <= set(context.privacy_exclusions):
            return "BLOCKED_PRIVACY_EXCLUSIONS_INCOMPLETE"

        included_classes = context.payload.get("included_classes", ())
        if not isinstance(included_classes, (list, tuple)):
            return "BLOCKED_CONTEXT_SCHEMA"
        if any(not isinstance(value, str) for value in included_classes):
            return "BLOCKED_CONTEXT_SCHEMA"
        if FORBIDDEN_CONTEXT_CLASSES & set(included_classes):
            return "BLOCKED_FORBIDDEN_CONTEXT_CLASS"
        return None

    def _find_backend(self, backend_class: str) -> BackendAdapter | None:
        matches: list[BackendAdapter] = []
        for backend in self.backends:
            capability = getattr(backend, "capability", None)
            if isinstance(capability, BackendCapabilityV1) and capability.backend_class == backend_class:
                matches.append(backend)
        if len(matches) != 1:
            return None
        return matches[0]

    @staticmethod
    def _ordered_backend_classes(policy: PolicyDecision) -> tuple[str, ...]:
        ordered: list[str] = []
        for policy_value in (policy.default, policy.fallback):
            backend_class = BACKEND_CLASS_BY_POLICY_VALUE[policy_value]
            if backend_class in P0_EXECUTABLE_BACKENDS and backend_class not in ordered:
                ordered.append(backend_class)
        return tuple(ordered)

    @staticmethod
    def _safe_request_digest(request: Any) -> str:
        try:
            return request.digest
        except Exception:
            safe = {
                "schema_id": REQUEST_SCHEMA,
                "schema_version": 1,
                "invalid_request": True,
                "request_id": _safe_text(getattr(request, "request_id", None)),
                "objective": _safe_text(getattr(request, "objective", None)),
                "model_policy_ref": _safe_text(getattr(request, "model_policy_ref", None)),
                "invalid_field_types": {
                    "required_evidence": type(getattr(request, "required_evidence", None)).__name__,
                    "required_privacy_exclusions": type(
                        getattr(request, "required_privacy_exclusions", None)
                    ).__name__,
                    "escalation_evidence": type(getattr(request, "escalation_evidence", None)).__name__,
                },
            }
            return _sha256_json(safe)

    @staticmethod
    def _base_receipt(
        request: InferenceRequestV1,
        *,
        status: str,
        policy: PolicyDecision | None,
        context: CompiledContextV1 | None,
        details: Mapping[str, Any] | None = None,
        model_calls: int = 0,
        uncertainty: tuple[str, ...] | list[str] = (),
        counterevidence: tuple[str, ...] | list[str] = (),
    ) -> dict[str, Any]:
        request_id = _safe_text(getattr(request, "request_id", None))
        request_policy_ref = _safe_text(getattr(request, "model_policy_ref", None))
        expected_policy_sha256 = _safe_text(getattr(request, "expected_policy_sha256", None))
        bound_context_digest = _safe_text(getattr(request, "bound_context_digest", None))

        receipt = {
            "schema_id": RECEIPT_SCHEMA,
            "schema_version": 1,
            "status": status,
            "request_digest": LocalInferenceGateway._safe_request_digest(request),
            "request_id": request_id,
            "policy_ref": policy.policy_ref if policy else request_policy_ref,
            "policy_digest": policy.policy_blob_digest if policy else expected_policy_sha256,
            "policy_currentness": policy.currentness if policy else "UNKNOWN",
            "context_digest": context.digest if context else bound_context_digest,
            "context_reopen_refs": list(context.reopen_refs) if context else [],
            "backend": None,
            "backend_capability_digest": None,
            "model_calls": model_calls,
            "output_digest": None,
            "uncertainty": list(uncertainty),
            "counterevidence": list(counterevidence),
            "measurement_class": "UNKNOWN",
            "measurements": {},
            "effect_state": NONAUTHORITY_EFFECT_STATE,
            "production_mutation": False,
            "runtime_authority": False,
            "provider_authority": False,
            "human_gate": False,
            "details": _json_plain(details or {}),
        }
        receipt["receipt_digest"] = _sha256_json(receipt)
        return receipt

    def _blocked_receipt(
        self,
        request: InferenceRequestV1,
        status: str,
        *,
        policy: PolicyDecision | None = None,
        context: CompiledContextV1 | None = None,
        details: Mapping[str, Any] | None = None,
        model_calls: int = 0,
        uncertainty: tuple[str, ...] | list[str] = (),
        counterevidence: tuple[str, ...] | list[str] = (),
    ) -> dict[str, Any]:
        return self._base_receipt(
            request,
            status=status,
            policy=policy,
            context=context,
            details=details,
            model_calls=model_calls,
            uncertainty=uncertainty,
            counterevidence=counterevidence,
        )

    @staticmethod
    def _success_receipt(
        *,
        request: InferenceRequestV1,
        policy: PolicyDecision,
        context: CompiledContextV1,
        capability: BackendCapabilityV1,
        result: BackendResultV1,
        attempts: list[dict[str, Any]],
        model_calls: int,
    ) -> dict[str, Any]:
        receipt = {
            "schema_id": RECEIPT_SCHEMA,
            "schema_version": 1,
            "status": "SATISFIED",
            "request_digest": request.digest,
            "request_id": request.request_id,
            "policy_ref": policy.policy_ref,
            "policy_digest": policy.policy_blob_digest,
            "policy_currentness": policy.currentness,
            "context_digest": context.digest,
            "context_reopen_refs": list(context.reopen_refs),
            "backend": {
                "backend_id": capability.backend_id,
                "backend_class": capability.backend_class,
                "artifact_ref": capability.artifact_ref,
                "network_required": capability.network_required,
            },
            "backend_capability_digest": capability.digest,
            "model_calls": model_calls,
            "output_digest": _sha256_bytes(result.output.encode("utf-8")),
            "output": result.output,
            "uncertainty": list(result.uncertainty),
            "counterevidence": list(result.counterevidence),
            "measurement_class": result.measurement_class,
            "measurements": _json_plain(result.measurements),
            "attempts": list(attempts),
            "effect_state": NONAUTHORITY_EFFECT_STATE,
            "production_mutation": False,
            "runtime_authority": False,
            "provider_authority": False,
            "human_gate": False,
            "details": {},
        }
        receipt["receipt_digest"] = _sha256_json(receipt)
        return receipt
